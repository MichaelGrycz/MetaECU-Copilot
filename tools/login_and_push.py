import subprocess
import webbrowser
import time
import sys

print("=" * 60)
print("GitHub One-Click Authorization & Auto-Push")
print("=" * 60)

# Run gh auth login --web in background process
proc = subprocess.Popen(
    ["gh", "auth", "login", "--web", "-h", "github.com", "-p", "https", "-s", "repo"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

code = None
for line in proc.stdout:
    print(line, end="")
    if "one-time code:" in line:
        code = line.split("one-time code:")[1].strip()
        print(f"\n--> TWOJ KOD: {code} <---\n")
        webbrowser.open("https://github.com/login/device")
        break

print("Czekam na klikniecie 'Authorize' w przegladarce...")
proc.wait()

print("\nAutoryzacja udana! Wysylam kod na GitHub...")
push_proc = subprocess.run(["git", "push", "-u", "origin", "main"], cwd="dist/MetaECU-Copilot", capture_output=True, text=True)
print(push_proc.stdout)
print(push_proc.stderr)

if push_proc.returncode == 0:
    print("\nSUCCESS: Caly projekt wyladowal na https://github.com/MichaelGrycz/MetaECU-Copilot !")
else:
    print("Blad push:", push_proc.stderr)
