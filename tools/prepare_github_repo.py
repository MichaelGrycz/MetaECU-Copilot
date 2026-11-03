#!/usr/bin/env python3
"""Export clean, standalone hackathon repository ready for public GitHub submission.

In accordance with Meta Global AI Developer Hackathon Rules:
- "New work only. Everything you present has to be built during the hackathon, Oct 26 to Nov 4."
- "Identify your contributions. Public repo required."

This tool isolates the exact code, assets, and documentation built during the event,
leaving behind local VM images, personal notes, and unrelated platforms.
Output is placed in: dist/MetaECU-Copilot/
"""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "dist" / "MetaECU-Copilot"


def _handle_remove_readonly(func, path, excinfo):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


# Exact files and directories built for the hackathon
INCLUDED = [
    ".github",
    "backend",
    "tools",
    "demo_assets",
    "build_assets",
    "main.py",
    "web_app.py",
    "modal_deploy.py",
    "run_desktop.py",
    "build_exe.py",
    "requirements.txt",
    "README.md",
    "DEPLOYMENT.md",
    ".env.example",
    ".gitignore",
]


def prepare_repo():
    print(f"Preparing pristine GitHub repository in: {EXPORT_DIR}")
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR, onexc=_handle_remove_readonly)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    for item in INCLUDED:
        src = ROOT / item
        dst = EXPORT_DIR / item
        if not src.exists():
            print(f"Warning: {item} does not exist, skipping.")
            continue
        if src.is_dir():
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", ".pytest_cache", ".git"
                ),
            )
        else:
            shutil.copy2(src, dst)
        print(f"  + Included: {item}")

    # Streamline README.md for hackathon submission (strip legacy multi-vehicle archives)
    readme_dst = EXPORT_DIR / "README.md"
    if readme_dst.exists():
        txt = readme_dst.read_text(encoding="utf-8")
        if "> The multi-vehicle repository overview" in txt:
            clean_txt = txt.split("> The multi-vehicle repository overview")[0].strip()
            clean_txt += """

---

## 🏆 Hackathon Submission Metadata

- **Event:** Meta Global AI Developer Hackathon (Oct 26 – Nov 4, 2026)
- **Track:** Indie Developer
- **Theme:** Build for Your World & Push the Frontier
- **Author:** Michał Grycz (Solo Builder)
- **Live Product URL:** https://michaelgrycz--metaecu-copilot-web.us-east.modal.run
- **Repository:** https://github.com/MichaelGrycz/MetaECU-Copilot
- **License:** MIT License (Open Source)
"""
            readme_dst.write_text(clean_txt, encoding="utf-8")

    # Ensure .env is never copied
    env_file = EXPORT_DIR / ".env"
    if env_file.exists():
        env_file.unlink()

    print("\n" + "=" * 65)
    print("SUCCESS: Pristine GitHub Repository Created!")
    print(f"Location: {EXPORT_DIR}")
    print("\nTo publish to your public GitHub account:")
    print(f"  cd {EXPORT_DIR}")
    print("  git init")
    print("  git add .")
    print(
        '  git commit -m "feat: MetaECU Copilot - Autonomous & Verifiable Calibration Engine"'
    )
    print("  git branch -M main")
    print("  git remote add origin https://github.com/MichalGrycz/MetaECU-Copilot.git")
    print("  git push -u origin main")
    print("=" * 65)


if __name__ == "__main__":
    prepare_repo()
