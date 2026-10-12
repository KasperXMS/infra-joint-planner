import subprocess,sys
from pathlib import Path
from runtime_guard import register
root=Path("/root/autodl-tmp/xiaoming/planning-skills-research-v1/run-001")
register(root,"development_queue")
for experiment in ("role-placement-v1","decision-context-probe-v1"):
 subprocess.run([sys.executable,str(root/"code/launch_experiment.py"),"--root",str(root),"--config",str(root/"configs"/(experiment+".json"))],check=True)
