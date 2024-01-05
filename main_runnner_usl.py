import os
import subprocess

subnames = [x.split(".")[0] for x in os.listdir("config/")]
ps_output = [x for x in os.popen('ps -ef | grep \&\&\ python3\ runner_usl.py\ ').read().splitlines() if 'grep' not in x]
for subname in subnames:
	if subname == 'funkoppopmod':
		continue
	if not any([subname + " " in x for x in ps_output]):
		subprocess.Popen(['python3', 'runner_usl.py', subname])
