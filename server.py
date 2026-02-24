import os
import time
import requests
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")


# ==========================================================
# LOAD MOD MANIFEST
# ==========================================================

def load_mod_manifest(game):

    try:
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{game}/mod.json"

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3.raw"
        }

        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            return r.json()

    except:
        pass

    return None


# ==========================================================
# CHECK MOD ACCESS
# ==========================================================

@app.route("/check_mod", methods=["POST"])
def check_mod():

    data = request.json

    game = data.get("game")
    token = data.get("token")

    mod = load_mod_manifest(game)

    if not mod:
        return jsonify({"allowed": False, "error": "Mod not found"}), 404

    now = int(time.time())

    # Public release = allow immediately
    if mod.get("release_timestamp", 0) <= now:
        return jsonify({
            "allowed": True,
            "version": mod.get("version")
        })

    # Locked content (future Patreon/SubStar logic goes here)

    if not token:
        return jsonify({"allowed": False, "error": "Auth required"}), 403

    return jsonify({"allowed": True})


# ==========================================================
# STREAM FILES FROM GITHUB
# ==========================================================

@app.route("/download/<path:path>")
def download(path):

    url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{path}"

    headers = {}

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    r = requests.get(url, headers=headers, stream=True)

    return Response(r.iter_content(chunk_size=8192))


# ==========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
