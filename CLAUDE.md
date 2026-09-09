# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The Skydive Mesquite Raspberry Pi media server: the shell scripts that package and publish jump media, the restoration guide for rebuilding the whole thing, and a Flask web UI that lets staff upload footage, run the scripts, and e-mail download links without SSH.

`scripts/` is the single source for the three shell scripts. `install.sh` copies them to `/usr/bin` on the Pi, and the Dockerfile copies the same files into the container, so the command line and the web UI always run identical code.

## Running the app

```bash
# Everything: scripts, configs, nginx, container
sudo ./install.sh

# Just the shell scripts, leaving the UI alone
sudo SKIP_UI=1 ./install.sh

# The container by itself
docker compose up -d --build
docker compose logs -f
```

The container binds to `127.0.0.1:5000`. Nginx proxies `/ui` to it (see `nginx/ui.conf`).

Local dev without Docker:
```bash
cd webapp
python3 -m venv venv && venv/bin/pip install -r requirements.txt
SECRET_KEY=dev ADMIN_USER=admin ADMIN_PASSWORD=admin STAFF_USER=user STAFF_PASSWORD=user \
  venv/bin/flask --app app run --port 5000
```

## .env (not in git — install.sh creates it from .env.example)

```
MONOLITH_UID=1000        # from: id monolith
MONOLITH_GID=1000
SECRET_KEY=...           # python3 -c "import secrets; print(secrets.token_hex(32))"
ADMIN_USER=admin
ADMIN_PASSWORD=...
STAFF_USER=user
STAFF_PASSWORD=...
```

## Architecture

```
Browser → Nginx (HTTPS, skydivingstuff.com)
            └── proxy_pass 127.0.0.1:5000
                    └── Flask/gunicorn (Docker, user=monolith)
                            ├── /ui/login|logout     — session auth
                            ├── /ui/funjumper        — upload + email links (all staff)
                            ├── /ui/upload           — XHR file upload to NFS (all staff)
                            ├── /ui/tandem           — upload + run zipandmove (admin)
                            ├── /ui/links            — read media-files list (admin)
                            └── /ui/logs             — tail 3 log files (admin)
```

Staff on the same LAN can also access `http://monolith.local:8080/ui/` (see `nginx/local.conf`).

## Authentication

Flask session auth — no Nginx `auth_basic`. Users are loaded from env vars at startup into the `USERS` dict. Two decorators enforce access:

- `@login_required` — any logged-in user
- `@admin_required` — `is_admin: True` users only

`ADMIN_USER` maps to `is_admin: True`; `STAFF_USER` maps to `is_admin: False`. The `is_admin` flag is injected into every template via `inject_user()` context processor and controls which nav links and dashboard cards render.

## Script execution

`run_script()` calls `subprocess.run` with combined stdout/stderr and a 300s timeout. Scripts use `flock` internally — a second concurrent trigger exits non-zero and shows a red result page, which is correct behavior. Both scripts exit early with code 0 when their source directory has no subdirectories to process.

## File uploads

`POST /ui/upload` accepts multipart files, a `folder_name`, and a `destination` (`share` or `funjumper`). Uploading to `share` requires `is_admin`. Folder names have spaces replaced with `_` before `secure_filename()` (otherwise `secure_filename` silently strips spaces). Files are flattened into `destination/folder_name/`. The Nginx upload location sets `client_max_body_size 0` and `proxy_request_buffering off` to stream large video files.

The Fun Jumper page warns (JS `confirm()`) if the user tries to send links without having uploaded in the current browser session.

## Mail

The container and the Pi both send mail directly to Gmail via msmtp (smtp.gmail.com:587, App Password). The Pi's `/etc/msmtprc` is mounted into the container read-only. `docker/msmtprc.example` is the template; the real file exists only on the Pi and is git-ignored. `/var/log/msmtp` is bind-mounted so both the container and Pi-direct runs log to the same file.

`/etc/msmtprc` must stay readable by the `monolith` user, since `zipandmove` and `funjumper` run as that user and the container runs with the same UID. `chmod 600` owned by `monolith` is right; chowning it to root would silently break sending.

## funjumper --emails flag

`scripts/funjumper` adds `--emails addr1 addr2 ...` to skip the interactive prompt when called from the web UI. Running it with no args preserves the original CLI behaviour.

## Credentials

This repository is public. Nothing with a real credential in it is tracked:

| Real file (git-ignored, on the Pi) | Template in git |
|---|---|
| `.env` | `.env.example` |
| `/etc/msmtprc` | `docker/msmtprc.example` |
| `/etc/skydive-media.conf` | `skydive-media.conf.example` |

`.githooks/pre-commit` refuses commits containing tokens, private keys, URLs with embedded passwords, or those live files. Enable it in a fresh clone with `git config core.hooksPath .githooks`. `install.sh` warns when a value on the Pi is still blank.

## Key constraint: UID matching

The container runs as `monolith` with the UID/GID from `.env`. This must match the Pi host's `monolith` user so bind-mounted NFS directories (`/media/nfs/*`) are writable without permission errors.

## NFS volume mounts

| Host path | Purpose |
|---|---|
| `/media/nfs/share` | Input for `zipandmove` |
| `/media/nfs/web` | Web-accessible zips + `media-files` links list |
| `/media/nfs/backed` | Backup storage |
| `/media/nfs/funjumper` | Input for `funjumper` |
| `/home/monolith/zipandmove` | Script logs and lock files |
| `/var/log/rpi_backup.log` | Read-only; shown on Logs page |
| `/etc/msmtprc` | Read-only; Gmail SMTP config |
| `/var/log/msmtp` | msmtp log (shared with Pi; created by msmtp on first use — no manual setup needed) |
