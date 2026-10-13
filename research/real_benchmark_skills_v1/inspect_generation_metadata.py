"""Read-only remote accounting check; does not export prompt hashes or text."""
import json
from pathlib import Path

path = Path('/root/autodl-tmp/real-benchmark-skills-v1/private/generation-metadata.jsonl')
records = [json.loads(line) for line in path.read_text().splitlines()]
print(json.dumps({'record_count': len(records), 'schema_keys': sorted(records[-1]) if records else [],
                  'first_epoch': records[0]['started_epoch'] if records else None,
                  'last_epoch': records[-1]['started_epoch'] if records else None,
                  'total_prompt_tokens': sum(r.get('prompt_tokens', 0) for r in records),
                  'total_generated_tokens': sum(r.get('generated_tokens', 0) for r in records),
                  'total_generation_seconds': sum(r.get('generation_seconds', 0) for r in records)}))
