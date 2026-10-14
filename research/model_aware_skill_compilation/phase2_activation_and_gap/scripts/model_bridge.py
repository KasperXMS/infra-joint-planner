"""Raw HTTP relay from study Docker network to the AutoDL loopback vLLM over SSH.

No prompt, tool schema, model parameter, or response transformation is performed.
Credential source stays outside Docker; request/response bodies and diagnostics stay
in a private WSL directory. This is an experimental transport, not a public API.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import secrets
import shlex
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import paramiko


PINNED_KEY_SHA256 = '962677eaf342b0d70d757796b387fe83964884f33f66284ff37e2fc6cf1496a7'


def credentials_from(path: Path) -> tuple[str, int, str]:
    source = path.read_text(encoding='utf-8-sig')
    section = source.split('AutoDL leased 2x RTX5090:', 1)[1]
    command = re.search(r'^command\s*:\s*(.+)$', section, re.M | re.I).group(1).strip()
    password = re.search(r'^password\s*:\s*(.+)$', section, re.M | re.I).group(1).strip()
    parts = shlex.split(command)
    port = int(parts[parts.index('-p') + 1])
    host = next(part.split('@', 1)[1] for part in parts if part.startswith('root@'))
    return host, port, password


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--credentials', required=True, type=Path)
    parser.add_argument('--private', required=True, type=Path)
    parser.add_argument('--bind', default='172.17.0.1')
    parser.add_argument('--port', type=int, default=18081)
    parser.add_argument('--upstream-port', type=int, default=18081)
    args = parser.parse_args()
    os.umask(0o077)
    args.private.mkdir(parents=True, exist_ok=True)
    key_path = args.private / 'bridge.key'
    if not key_path.exists():
        key_path.write_text(secrets.token_hex(32) + '\n')
    token = key_path.read_text().strip()
    host, port, password = credentials_from(args.credentials)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, port=port, username='root', password=password,
                   look_for_keys=False, allow_agent=False, timeout=20,
                   auth_timeout=20, banner_timeout=20)
    transport = client.get_transport()
    fingerprint = hashlib.sha256(transport.get_remote_server_key().asbytes()).hexdigest()
    if fingerprint != PINNED_KEY_SHA256:
        client.close()
        raise RuntimeError('SSH host key differs from the inspected new instance')
    transport.set_keepalive(20)
    summary_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *_: object) -> None:
            pass

        def do_GET(self) -> None:
            self.relay()

        def do_POST(self) -> None:
            self.relay()

        def relay(self) -> None:
            if self.headers.get('Authorization') != 'Bearer ' + token:
                self.send_error(401)
                return
            if not re.fullmatch(r'/v1/(models|chat/completions|responses)', self.path):
                self.send_error(404)
                return
            request_id = uuid.uuid4().hex
            raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
            request_dir = args.private / 'requests'
            request_dir.mkdir(exist_ok=True)
            (request_dir / (request_id + '.request.bin')).write_bytes(raw)
            started = time.time()
            status = None
            count = 0
            error = None
            first_byte_seconds = None
            conn = http.client.HTTPConnection('127.0.0.1', args.upstream_port, timeout=300)
            try:
                conn.sock = transport.open_channel('direct-tcpip',
                    ('127.0.0.1', args.upstream_port), ('127.0.0.1', 0), timeout=30)
                conn.sock.settimeout(300)
                conn.request(self.command, self.path, body=raw or None,
                    headers={'Content-Type': self.headers.get('Content-Type', 'application/json'),
                             'Authorization': 'Bearer local-study'})
                response = conn.getresponse()
                status = response.status
                self.send_response(status)
                self.send_header('Content-Type', response.getheader('Content-Type', 'application/json'))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.close_connection = True
                with (request_dir / (request_id + '.response.bin')).open('wb') as out:
                    first = response.read(1)
                    if first:
                        first_byte_seconds = time.time() - started
                        count += len(first)
                        out.write(first)
                        self.wfile.write(first)
                        self.wfile.flush()
                    while chunk := response.read(4096):
                        count += len(chunk)
                        out.write(chunk)
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except Exception as exc:
                error = type(exc).__name__ + ': ' + str(exc)[:300]
                self.close_connection = True
                if status is None:
                    self.send_error(502)
            finally:
                conn.close()
                record = {'id': request_id, 'run_id': self.headers.get('X-Study-Run-ID'),
                          'route': self.path, 'started_epoch': started,
                          'seconds': time.time() - started, 'status': status,
                          'first_byte_seconds': first_byte_seconds,
                          'request_bytes': len(raw), 'response_bytes': count,
                          'request_sha256': hashlib.sha256(raw).hexdigest(), 'error': error}
                with summary_lock, (args.private / 'requests.jsonl').open('a') as out:
                    out.write(json.dumps(record) + '\n')

    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    print(json.dumps({'state': 'listening', 'bind': args.bind, 'port': args.port,
                      'private': str(args.private)}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        client.close()


if __name__ == '__main__':
    main()
