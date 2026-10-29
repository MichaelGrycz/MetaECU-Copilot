# MetaECU Copilot — Deployment Guide

Three ways to run the product. All of them run the same deterministic engine:
Meta Muse plans, the Safety Gate decides, physics has the final word.

| Form factor | Command | Result |
|---|---|---|
| **Live Product (cloud)** | `modal deploy modal_deploy.py` | Public HTTPS URL for the Cerebral Valley submission form |
| **Desktop app (no console)** | double-click `dist/MetaECU_Copilot.exe` | Native Windows window "MetaECU Copilot — Motorsport Studio" |
| **Desktop from source** | `python run_desktop.py` | Same native window, no CMD needed afterwards |
| **PWA** | open the URL in Chrome/Edge → *Install app* | Desktop icon on Windows / macOS |
| **Headless CLI** | `python main.py --intent "..."` | Pipeline + report, no UI |

---

## 0. What gets packaged (important)

The full vehicle workspace is ~14 GB (WinOLS VM images). The cockpit only
needs **five files** (~12.7 MB). Stage them once:

```bash
python tools/stage_assets.py   # -> build_assets/metaecu_assets/ (+ checksum manifest)
python tools/make_icon.py      # -> assets/metaecu.ico + PWA icons
```

Both Modal and PyInstaller consume the staged tree via `METAECU_ASSET_ROOT`.
Output binaries/reports are written to a writable dir (`METAECU_OUTPUT_DIR`,
default `%TEMP%/metaecu_web`; `/tmp/metaecu_web` on Modal).

---

## 1. Desktop app — one click, no CMD

### Option A: prebuilt executable

```bash
pip install -r requirements.txt
python build_exe.py            # ~3 min -> dist/MetaECU_Copilot.exe (one file)
```

Double-click `MetaECU_Copilot.exe`. A native window opens with the cockpit —
no console, no address bar, custom motorsport icon (turbo wheel). The server
binds an ephemeral localhost port, so it never clashes with other apps.

Verified during development: the frozen EXE was launched headlessly and
answered `/api/meta` with checksum `0xD01FE500` over HTTP.

### Option B: from source

```bash
python run_desktop.py            # pywebview window
python run_desktop.py --browser  # fallback: system browser
python run_desktop.py --smoke    # CI check: boots the embedded server, exits 0
```

### Option C: PWA install

Serve the cockpit any way (Modal URL, `python web_app.py`, or the desktop
window), open it in Chrome/Edge, then use the **⬇ INSTALL APP** button or the
browser's install icon. The app installs with the turbo icon and runs
standalone. The service worker keeps calibration API calls network-only —
dyno/binary data is never cached.

---

## 2. Modal cloud deployment — public HTTPS Live Product

Judges open a link. This is that link. Modal terminates TLS automatically;
the app itself needs no GPU (numpy map math only) — 1 CPU / 1 GiB keeps the
$100 hackathon credit essentially untouched.

### One-time setup

```bash
pip install modal
modal setup                                   # browser auth, creates ~/.modal.toml
modal secret create meta-secret META_API_KEY=<your-meta-key>
# optional: META_API_BASE_URL=https://api.meta.ai/v1 (default if unset)
```

Without the secret the deployment still works: planning falls back to the
deterministic offline planner and the Safety Gate + 450 Nm intercept demo
(`?demo=1`) remain fully functional. The secret is what enables live
Muse Spark reasoning and Meta Vision.

### Deploy

```bash
python modal_deploy.py --smoke   # offline pre-flight: packaged app must PASS
modal deploy modal_deploy.py     # first build: ~2-4 min (image + assets)
```

Modal prints the public URL, of the form:

```
https://<your-workspace>--metaecu-copilot-web.modal.run
```

Paste that URL into the Cerebral Valley submission form as the **Live
Product** link. Judges get the full cockpit: drag-and-drop `.bin`, 3D map
explorer, Thought Stream, the pulsing Safety Gate intercept and Flash &
Export — no install, no login.

### Iterate

```bash
modal serve modal_deploy.py      # ephemeral dev URL with hot reload
modal app list                   # inspect deployments
modal app stop metaecu-copilot   # tear down
```

### Notes for the demo

- Container cold start is a few seconds; open the URL once before recording.
- Scale-down window is 120 s; ephemeral sessions (`modal serve`) avoid any
  idle cost while iterating.
- Uploads are capped by the app itself (2 MiB flash validation) — malformed
  binaries get a clean HTTP 400, never a stack trace.
