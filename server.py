import os
import time
import requests
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")

RAW_BASE = f"https://raw.githubusercontent.com/{REPO_NAME}/main"


# ==========================================================
# LOAD MOD MANIFEST
# ==========================================================

def load_mod_manifest(game):

    try:
        url = f"{RAW_BASE}/{game}/mod.json"

        r = requests.get(url)

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

    data = request.json or {}

    game = data.get("game")
    user_tier = data.get("tier", "follower")

    mod = load_mod_manifest(game)

    if not mod:
        return jsonify({"allowed": False, "error": "Mod not found"}), 404

    now = int(time.time())

    # Public release check
    release_time = mod.get("release_timestamp", 0)

    if release_time <= now:
        return jsonify({
            "allowed": True,
            "version": mod.get("version"),
            "auto_install": mod.get("auto_install", False)
        })

    # Tier locked content (future logic)
    tier_map = ["follower", "bronze", "silver", "gold"]

    mod_tier = "gold"  # default lock tier (expand later)

    if user_tier not in tier_map:
        return jsonify({"allowed": False, "error": "Invalid tier"}), 403

    if tier_map.index(user_tier) < tier_map.index(mod_tier):
        return jsonify({"allowed": False, "error": "Tier locked"}), 403

    return jsonify({
        "allowed": True,
        "version": mod.get("version")
    })


# ==========================================================
# STREAM FILES FROM GITHUB
# ==========================================================

@app.route("/download/<path:path>")
def download(path):

    url = f"{RAW_BASE}/{path}"

    headers = {}

    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    r = requests.get(url, headers=headers, stream=True)

    if r.status_code != 200:
        return "File not found", 404

    return Response(
        r.iter_content(chunk_size=8192),
        content_type=r.headers.get("content-type")
    )


# ==========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
