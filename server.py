"""推文日报 Web 服务器"""
import json, os, socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from flask import Flask, jsonify, send_from_directory

DATA_DIR = Path(__file__).parent / "data"
STATIC_DIR = Path(__file__).parent / "static"
CST = timezone(timedelta(hours=8))

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")

@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")

@app.route("/api/digest")
def api_digest():
    result = {}
    if not DATA_DIR.exists():
        return jsonify(result)
    for f in sorted(DATA_DIR.glob("*.json"), reverse=True):
        try:
            day = json.loads(f.read_text(encoding="utf-8"))
            result[f.stem] = day
        except Exception:
            continue
    return jsonify(result)

@app.route("/api/info")
def api_info():
    port = int(os.environ.get("PORT", "8080"))
    return jsonify({
        "localUrl": f"http://localhost:{port}",
        "lanUrl": f"http://{get_local_ip()}:{port}",
        "user": "whyyoutouzhele",
    })

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    print(f"桌面访问: http://localhost:{port}")
    print(f"手机访问: http://{get_local_ip()}:{port}")
    app.run(host=host, port=port, debug=False)
