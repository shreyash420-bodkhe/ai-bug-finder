import subprocess

user_command = "echo deployment started"
subprocess.run(user_command, shell=True, check=True)
