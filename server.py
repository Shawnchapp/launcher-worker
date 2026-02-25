import os
import time
import requests
import hashlib
import json
from urllib.parse import quote
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv

# ==========================================================
# LOAD ENV
# ==========================================================

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
        if not game:
            return None

        safe_game = quote(game)

        url = f"{RAW_BASE}/{safe_game}/mod.json"

        headers = {}

        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        r = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        if r.ok:
            return r.json()

    except:
        pass

    return None

@app.route("/mods_list", methods=["GET"])
def mods_list():

    mods = []

    try:
        repo_url = f"https://api.github.com/repos/{REPO_NAME}/contents"

        headers = {}

        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        r = requests.get(repo_url, headers=headers, timeout=10)

        if r.ok:
            data = r.json()

            for item in data:
                if item["type"] == "dir":

                    game_name = item["name"]

                    # Load mod.json for each mod
                    mod = load_mod_manifest(game_name)

                    if mod:
                        mods.append({
                            "name": game_name,
                            "version": mod.get("version")
                        })

    except:
        pass

    # Create stable JSON string for hashing
    mods_sorted = sorted(mods, key=lambda x: x["name"])
    json_string = json.dumps(mods_sorted, separators=(",", ":"))

    hash_value = hashlib.md5(json_string.encode()).hexdigest()

    return jsonify({
        "hash": hash_value,
        "mods": mods_sorted
    })
# ==========================================================
# CHECK MOD ACCESS
# ==========================================================

@app.route("/check_mod", methods=["POST"])
def check_mod():

    data = request.json or {}

    game = data.get("game")
    user_tier = data.get("tier", "follower")

    if not game:
        return jsonify({"allowed": False, "error": "Missing game"}), 400

    mod = load_mod_manifest(game)

    if not mod:
        return jsonify({"allowed": False, "error": "Mod not found"}), 404

    now = int(time.time())

    release_time = mod.get("release_timestamp", 0)

    # ==================================================
    # PUBLIC RELEASE CHECK
    # ==================================================

    if release_time <= now:
        return jsonify({
            "allowed": True,
            "version": mod.get("version"),
            "auto_install": mod.get("auto_install", False)
        })

    # ==================================================
    # TIER LOCK CHECK
    # ==================================================

    tier_map = ["follower", "bronze", "silver", "gold"]

    mod_tier = mod.get("tier_required", "gold")

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

    if ".." in path or path.startswith("/"):
        return jsonify({"error": "Invalid path"}), 400

    safe_path = quote(path)

    url = f"{RAW_BASE}/{safe_path}"

    headers = {}

    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    r = requests.get(
        url,
        headers=headers,
        stream=True,
        timeout=15
    )

    if not r.ok:
        return jsonify({"error": "File not found"}), 404

    return Response(
        r.iter_content(chunk_size=8192),
        content_type=r.headers.get("content-type"),
        direct_passthrough=True
    )


# ==========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
