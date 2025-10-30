import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from sukoon_rag_pinecone_gemini import handle_user_input


app = Flask(__name__)


@app.get("/")
def landing():
    return render_template("landing_softland.html")


@app.get("/chat")
def chat():
    return render_template("index.html")


@app.get("/softland/<path:filename>")
def softland_static(filename: str):
    base_dir = os.path.join(app.root_path, "softland-free-lite")
    return send_from_directory(base_dir, filename)


@app.post("/api/chat")
def api_chat():
    try:
        data = request.get_json(silent=True) or {}
        user_input = (data.get("message") or "").strip()
        if not user_input:
            return jsonify({"error": "Message is required"}), 400
        reply = handle_user_input(user_input)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # Note: in production, run with a WSGI server (e.g. gunicorn)
    app.run(host="0.0.0.0", port=8000, debug=True)


