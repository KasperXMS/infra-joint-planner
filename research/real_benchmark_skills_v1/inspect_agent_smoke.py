import json
from pathlib import Path

root = Path("/root/skillsbench-local-20261013")
attempt = "agent-smoke-final-contract"
token = (root / "private/bridge.key").read_text().strip()
result = {"log": (root / "logs" / (attempt + ".log")).read_text(errors="replace")[-1800:].replace(token, "[REDACTED]")}
requests = root / "private/requests" / attempt
result["requests"] = []
if requests.exists():
    for path in requests.glob("*.request.json"):
        body = json.loads(path.read_bytes())
        response = path.with_name(path.name.replace(".request.json", ".response.bin"))
        item = {"id": path.stem, "request_bytes": path.stat().st_size, "model": body.get("model"),
                "temperature": body.get("temperature"), "max_tokens": body.get("max_tokens"),
                "messages": len(body.get("messages", [])), "tools": len(body.get("tools", [])),
                "response_bytes": response.stat().st_size if response.exists() else None}
        if response.exists() and response.stat().st_size:
            try:
                parsed = json.loads(response.read_bytes())
                item["finish_reason"] = parsed.get("choices", [{}])[0].get("finish_reason")
                item["error"] = parsed.get("error")
                item["usage"] = parsed.get("usage")
                calls = parsed.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
                item["tool_call_names"] = [c.get("function", {}).get("name") for c in calls]
                item["tool_argument_lengths"] = [len(c.get("function", {}).get("arguments", "")) for c in calls]
            except Exception:
                item["streaming_or_incomplete"] = True
        result["requests"].append(item)
result["files"] = [str(p.relative_to(root / "jobs" / attempt)) for p in (root / "jobs" / attempt).rglob("*") if p.is_file()][:45]
result["request_count"] = len(result["requests"])
result["completed_usage"] = {key: sum((r.get("usage") or {}).get(key, 0) for r in result["requests"])
                             for key in ("prompt_tokens", "completion_tokens")}
result["requests"] = result["requests"][-3:]
result["log"] = result["log"][-650:]
summary = root / "jobs" / attempt / "summary.json"
if summary.exists():
    data = json.loads(summary.read_bytes())
    result["summary"] = {k: data.get(k) for k in ("total", "passed", "failed", "errored", "error_categories", "verifier_errored", "elapsed_sec")}
print(json.dumps(result))
