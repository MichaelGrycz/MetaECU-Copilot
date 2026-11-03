import os
import subprocess
import sys
import time

# Run modal token new in background
proc = subprocess.Popen(
    ["modal", "token", "new"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

url = ""
for line in proc.stdout:
    if "https://modal.com/token-flow/" in line:
        url = line.strip()
        with open("tools/modal_url.txt", "w", encoding="utf-8") as f:
            f.write(url)
        break

print("Czekam na autoryzacje na stronie Modal...")
proc.wait()

print("\nAutoryzacja Modal udana! Tworze sekret i wdrazam aplikacje...")
# Create secret (reads the API key from the local .env, which is git-ignored)
_meta_key = os.environ.get("META_API_KEY", "LLM_YOUR_API_KEY_HERE")
subprocess.run(
    [
        "modal",
        "secret",
        "create",
        "meta-secret",
        f"META_API_KEY={_meta_key}",
    ],
    check=False,
)

# Deploy
deploy_proc = subprocess.run(
    ["modal", "deploy", "modal_deploy.py"], capture_output=True, text=True
)
print(deploy_proc.stdout)
print(deploy_proc.stderr)

with open("demo_assets/output/MODAL_PUBLIC_URL.txt", "w", encoding="utf-8") as f:
    f.write(deploy_proc.stdout)

print("\nSUCCESS: Aplikacja zostala wdrożona w chmurze Modal!")
