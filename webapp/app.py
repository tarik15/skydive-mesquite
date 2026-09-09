import functools
import hmac
import os
import re
import subprocess

from flask import Flask, jsonify, redirect, render_template, request, session
from werkzeug.utils import secure_filename

app = Flask(__name__, static_url_path="/ui/static")
# No fallback on purpose. This repository is public, so a default key would be
# a published key, and anyone could forge a session cookie with it. Failing to
# start is the safer outcome.
app.secret_key = os.environ.get("SECRET_KEY", "")
if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY is not set. Generate one with:\n"
        '  python3 -c "import secrets; print(secrets.token_hex(32))"\n'
        "and put it in .env next to docker-compose.yml."
    )

SCRIPTS = {
    "zipandmove": "/usr/bin/zipandmove",
    "funjumper": "/usr/bin/funjumper",
}
LOG_FILES = {
    "zipandmove": "/home/monolith/zipandmove/zipandmove.log",
    "funjumper": "/home/monolith/zipandmove/fun.log",
    "rpi_back": "/var/log/rpi_backup.log",
}
MEDIA_LINKS_FILE = "/media/nfs/web/media-files"
LOG_TAIL_LINES = 100

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(\.[A-Za-z]{2,})?$")
URL_RE = re.compile(r"(https?://\S+)")

UPLOAD_DESTINATIONS = {
    "share":     "/media/nfs/share",
    "funjumper": "/media/nfs/funjumper",
}

# Users loaded from environment variables
USERS = {}
_admin = os.environ.get("ADMIN_USER", "admin")
_admin_pw = os.environ.get("ADMIN_PASSWORD", "")
_staff = os.environ.get("STAFF_USER", "user")
_staff_pw = os.environ.get("STAFF_PASSWORD", "")
if _admin and _admin_pw:
    USERS[_admin] = {"password": _admin_pw, "is_admin": True}
if _staff and _staff_pw:
    USERS[_staff] = {"password": _staff_pw, "is_admin": False}


def _check_password(stored, given):
    return hmac.compare_digest(stored.encode(), given.encode())


def login_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect("/ui/login")
        return f(*args, **kwargs)
    return wrapped


def admin_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect("/ui/login")
        if not USERS.get(session["username"], {}).get("is_admin"):
            return redirect("/ui/")
        return f(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    username = session.get("username", "")
    is_admin = USERS.get(username, {}).get("is_admin", False)
    return {"current_user": username, "is_admin": is_admin}


def run_script(cmd):
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
    )
    return result.returncode, result.stdout


def tail_file(path, n=LOG_TAIL_LINES):
    try:
        result = subprocess.run(
            f"tail -n {n} {path} | tac",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout or "(empty)"
    except Exception as e:
        return f"(could not read {path}: {e})"


@app.route("/ui/login", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect("/ui/")
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = USERS.get(username)
        if user and _check_password(user["password"], password):
            session["username"] = username
            return redirect("/ui/")
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/ui/logout")
def logout():
    session.clear()
    return redirect("/ui/login")


@app.route("/ui/")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/ui/zipandmove", methods=["POST"])
@admin_required
def trigger_zipandmove():
    rc, out = run_script([SCRIPTS["zipandmove"]])
    return render_template("result.html", script="zipandmove", rc=rc, output=out)


@app.route("/ui/funjumper", methods=["GET", "POST"])
@login_required
def trigger_funjumper():
    if request.method == "GET":
        return render_template("funjumper.html")

    raw = request.form.get("emails", "")
    addrs = re.split(r"[\s,]+", raw.strip())
    addrs = [a for a in addrs if a]
    invalid = [a for a in addrs if not EMAIL_RE.match(a)]

    if not addrs:
        return render_template("funjumper.html", error="Please enter at least one email address.")
    if invalid:
        return render_template("funjumper.html", error=f"Invalid address(es): {', '.join(invalid)}", prefill=raw)

    rc, out = run_script([SCRIPTS["funjumper"], "--emails"] + addrs)
    return render_template("result.html", script="funjumper", rc=rc, output=out)


@app.route("/ui/links")
@admin_required
def show_links():
    try:
        with open(MEDIA_LINKS_FILE) as f:
            raw_lines = [line.rstrip() for line in f if line.strip()][::-1]
    except FileNotFoundError:
        raw_lines = ["(no links file found)"]

    lines = []
    for line in raw_lines:
        m = URL_RE.search(line)
        if m:
            lines.append((line[: m.start()], m.group(1)))
        else:
            lines.append((line, None))

    return render_template("links.html", lines=lines)


@app.route("/ui/tandem")
@admin_required
def tandem():
    return render_template("tandem.html")


@app.route("/ui/logs")
@admin_required
def show_logs():
    logs = {name: tail_file(path) for name, path in LOG_FILES.items()}
    return render_template("logs.html", logs=logs)


@app.route("/ui/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "GET":
        return render_template("upload.html")

    destination = request.form.get("destination")
    folder_name = secure_filename(request.form.get("folder_name", "").strip().replace(" ", "_"))
    files = request.files.getlist("files")

    if destination not in UPLOAD_DESTINATIONS:
        return jsonify(error="Invalid destination."), 400
    if destination == "share" and not USERS.get(session.get("username", ""), {}).get("is_admin"):
        return jsonify(error="Admin access required for this destination."), 403
    if not folder_name:
        return jsonify(error="Folder name is required."), 400
    if not files or all(f.filename == "" for f in files):
        return jsonify(error="No files selected."), 400

    target_dir = os.path.join(UPLOAD_DESTINATIONS[destination], folder_name)
    os.makedirs(target_dir, exist_ok=True)

    saved = []
    for f in files:
        if not f.filename:
            continue
        name = secure_filename(os.path.basename(f.filename))
        if not name:
            continue
        dest_path = os.path.join(target_dir, name)
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(name)
            i = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(target_dir, f"{base}_{i}{ext}")
                i += 1
        f.save(dest_path)
        saved.append(os.path.basename(dest_path))

    return jsonify(count=len(saved), target=target_dir)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
