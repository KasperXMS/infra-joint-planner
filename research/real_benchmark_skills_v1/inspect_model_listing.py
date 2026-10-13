"""Check the relay's real model listing before automated model transition."""
import json
import urllib.request
from pathlib import Path

root = Path('/root/skillsbench-local-20261013')
key = (root / 'private/bridge.key').read_text().strip()
request = urllib.request.Request('http://172.17.0.1:18080/runs/development-transition/v1/models',
                                 headers={'Authorization': 'Bearer ' + key})
with urllib.request.urlopen(request, timeout=30) as response:
    data = json.load(response)
print(json.dumps({'keys': list(data), 'ids': [x.get('id') for x in data.get('data', [])]}))
