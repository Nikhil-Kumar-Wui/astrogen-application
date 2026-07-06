import subprocess
import sys
import time

import os
print("Launching AstroGen.exe...")
env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"
proc = subprocess.Popen(
    [r"c:\Users\harsh\Desktop\NTCC - In House\APPLICATION\APP 5\PROJECT1\dist\AstroGen\AstroGen.exe"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    env=env
)

# Read output in real-time
while True:
    # Check if process has terminated
    ret = proc.poll()
    
    # Read any available stdout/stderr
    while True:
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            print("STDOUT:", line.strip())
        else:
            break
            
    while True:
        line = proc.stderr.readline() if proc.stderr else ""
        if line:
            print("STDERR:", line.strip())
        else:
            break
            
    if ret is not None:
        print(f"Process terminated with exit code {ret}")
        break
        
    time.sleep(0.1)
