import os
import subprocess
import sys

proc = subprocess.Popen(
    ["gh", "auth", "login", "--web", "-h", "github.com", "-p", "https", "-s", "repo"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

code = ""
for line in proc.stdout:
    if "one-time code:" in line:
        code = line.split("one-time code:")[1].strip()
        with open("tools/current_code.txt", "w", encoding="utf-8") as f:
            f.write(code)
        break

# Wait in background for completion, then push
proc.wait()
subprocess.run(["git", "push", "-u", "origin", "main"], cwd="dist/MetaECU-Copilot")
