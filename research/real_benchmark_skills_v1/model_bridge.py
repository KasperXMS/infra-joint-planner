"""Authenticated WSL HTTP relay to loopback-only AutoDL inference over SSH.

Applies declared generation settings and the official Qwen3Coder argument decoder.
Prompts and tool schemas are unchanged; native and decoded responses are preserved.
Raw request/response bodies stay in a private workspace outside the repository.
"""
import argparse
import hashlib
import http.client
import json
import os
import re
import secrets
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import paramiko
from qwen3_coder_arguments import decode_arguments

ROOT = Path("/root/skillsbench-local-20261013")


def main(credentials: Path, known_hosts: Path, backend="vllm"):
    os.umask(0o077)
    private = ROOT / "private"
    private.mkdir(exist_ok=True)
    key_path = private / "bridge.key"
    if not key_path.exists():
        key_path.write_text(secrets.token_hex(32))
    token = key_path.read_text().strip()
    source = credentials.read_text(encoding="utf-8-sig")
    target = re.search(r"ssh[^\r\n]*root@connect\.westd\.seetacloud\.com[^\r\n]*", source)
    if target is None:
        raise RuntimeError("Configured AutoDL SSH target missing; file contents withheld")
    password = re.search(r"(?:password|passwd|密码|口令)\s*[:：=]\s*[`\x27\x22]?([^\s`\x27\x22]+)", source[target.start():], re.I)
    if password is None:
        raise RuntimeError("SSH credential not recognized; file contents withheld")
    client = paramiko.SSHClient()
    client.load_host_keys(str(known_hosts))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect("connect.westd.seetacloud.com", port=39059, username="root", password=password.group(1),
                   look_for_keys=False, allow_agent=False, timeout=20, auth_timeout=20, banner_timeout=20)
    transport = client.get_transport()
    transport.set_keepalive(20)
    summary_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        def do_GET(self):
            self.relay()

        def do_POST(self):
            self.relay()

        def relay(self):
            if self.headers.get("Authorization") != "Bearer " + token:
                self.send_error(401)
                return
            match = re.fullmatch(r"/runs/([a-zA-Z0-9_-]+)/v1/(chat/completions|models|study_status)", self.path)
            if match is None:
                self.send_error(404)
                return
            run_id, route = match.groups()
            request_id = uuid.uuid4().hex
            log_root = private / "requests" / run_id
            log_root.mkdir(parents=True, exist_ok=True)
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            body = json.loads(raw) if raw else None
            if body is not None:
                if body.get("stream"):
                    self.send_error(400, "Frozen harness uses non-streaming requests")
                    return
                if backend == "transformers":
                    name = body.get("model", "").rsplit("/", 1)[-1].split("@", 1)[0]
                    if name not in {"Qwen3.5-4B", "Qwen3.5-9B"}:
                        self.send_error(400, "Unknown frozen model")
                        return
                    body["model"] = "/root/autodl-tmp/real-benchmark-skills-v1/models/" + name
                body.update(temperature=0, max_tokens=4096, top_p=1, presence_penalty=0, frequency_penalty=0,
                            chat_template_kwargs={"enable_thinking": False})
                if body.get("stream"):
                    body["stream_options"] = {"include_usage": True}
                # No guided decoding or tool-schema rewrite. Standard parameter
                # decoding occurs only after generation and is logged below.
                if any(k in body for k in ("guided_json", "guided_regex", "structured_outputs")):
                    self.send_error(400, "Undeclared structured decoding")
                    return
                raw = json.dumps(body).encode()
                (log_root / (request_id + ".request.json")).write_bytes(raw)
            started = time.time()
            status = None
            received = 0
            error = None
            conversions = []
            conn = http.client.HTTPConnection("127.0.0.1", 18000, timeout=300)
            try:
                conn.sock = transport.open_channel("direct-tcpip", ("127.0.0.1", 18000), ("127.0.0.1", 0), timeout=30)
                conn.sock.settimeout(300)
                upstream_route = "/study/status" if route == "study_status" else "/v1/" + route
                conn.request(self.command, upstream_route, body=raw or None,
                             headers={"Content-Type": "application/json", "Authorization": "Bearer local-study"})
                response = conn.getresponse()
                status = response.status
                self.send_response(status)
                self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                with (log_root / (request_id + ".response.bin")).open("wb") as output:
                    if backend == "transformers" and route == "chat/completions" and status == 200:
                        native = response.read()
                        (log_root / (request_id + ".native-response.bin")).write_bytes(native)
                        decoded, conversions = decode_arguments(json.loads(native), body.get("tools"))
                        data = json.dumps(decoded, ensure_ascii=False).encode()
                        received += len(data)
                        output.write(data)
                        self.wfile.write(data)
                        self.wfile.flush()
                    else:
                        while data := response.read(65536):
                            received += len(data)
                            output.write(data)
                            self.wfile.write(data)
                            self.wfile.flush()
            except Exception as exc:
                error = type(exc).__name__
                self.close_connection = True
                if status is None:
                    self.send_error(502)
            finally:
                conn.close()
                record = {"request_id": request_id, "run_id": run_id, "started_epoch": started,
                          "latency_seconds": time.time() - started, "http_status": status,
                          "response_bytes": received, "error": error,
                          "official_parser_conversions": conversions,
                          "request_sha256": hashlib.sha256(raw).hexdigest(), "model": body.get("model") if body else None}
                with summary_lock, (private / "requests.jsonl").open("a") as output:
                    output.write(json.dumps(record) + "\n")

    server = ThreadingHTTPServer(("0.0.0.0", 18080), Handler)
    print(json.dumps({"status": "listening", "port": 18080, "backend": backend, "private_root": str(private)}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--known-hosts", type=Path, required=True)
    parser.add_argument("--backend", choices=["vllm", "transformers"], default="vllm")
    args = parser.parse_args()
    main(args.credentials, args.known_hosts, args.backend)
