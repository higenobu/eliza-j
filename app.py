#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Japanese ELIZA-like chat (Flask + Janome)
Run: python app.py
"""
import re
import time
import sqlite3
import os
from flask import Flask, render_template, request, jsonify, g
from janome.tokenizer import Tokenizer

DB_PATH = os.environ.get("CHAT_DB", "chat_logs_jp.db")
app = Flask(__name__, static_folder="static", template_folder="templates")
tokenizer = Tokenizer()

# --- simple pronoun reflections for Japanese ---
REFLECTIONS = {
    "わたし": "あなた", "私": "あなた",
    "ぼく": "あなた", "僕": "あなた",
    "おれ": "あなた", "俺": "あなた",
    "あなた": "わたし", "きみ": "わたし", "君": "わたし",
}

def reflect_jp(text: str) -> str:
    # tokenize and replace pronouns using a simple mapping
    tokens = [t.surface for t in tokenizer.tokenize(text)]
    out = []
    for t in tokens:
        out.append(REFLECTIONS.get(t, t))
    return "".join(out)

# --- pattern-response pairs (Japanese) ---
# %1 will be replaced with reflected captured group
PAIRS = [
    (re.compile(r'^(?:こんにちは|やあ|おはよう|こんばんは)[\s！!　]*', re.I),
     ["こんにちは。ご機嫌いかがですか？", "やあ。今日は何について話しますか？"]),
    (re.compile(r'^(?:私は|僕は|わたしは|俺は)\s*(.+)$'),
     ["そうですか、あなたは%1なのですね。もっと教えてください。"]),
    (re.compile(r'^(.*)が好きです$'),
     ["どうして%1が好きなのですか？", "%1について詳しく話してくれますか？"]),
    (re.compile(r'^(.*)が嫌いです$'),
     ["なぜ%1が嫌いなのですか？", "それはつらいですね。%1についてもう少し聞かせてください。"]),
    (re.compile(r'^(.*)したい$'),
     ["どうして%1したいのですか？", "%1することはあなたにとって何を意味しますか？"]),
    (re.compile(r'^(.*)\?+$'),
     ["そのことについてどう思いますか？", "その疑問は重要そうですね。なぜそう思いますか？"]),
    (re.compile(r'^(さようなら|バイバイ|じゃね|おやすみ)$', re.I),
     ["さようなら。また話しましょう。", "お話できてよかったです。"]),
]

FALLBACKS = [
    "詳しく聞かせてください。",
    "それについてもっと教えてください。",
    "なるほど、もう少し具体的に言えますか？",
    "興味深いですね。続けてください。"
]

# --- DB helpers ---
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH, check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at REAL NOT NULL
    )
    """)
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

# --- Bot logic ---
def bot_response(msg: str) -> str:
    s = msg.strip()
    if not s:
        return "何か話してください。"
    for pat, responses in PAIRS:
        m = pat.match(s)
        if m:
            # replace %1, %2 ... with reflected captures
            def repl(match):
                idx = int(match.group(1))
                try:
                    captured = m.group(idx)
                except IndexError:
                    captured = ""
                return reflect_jp(captured or "")
            # choose a random response
            import random
            resp = random.choice(responses)
            resp = re.sub(r"%([0-9])", repl, resp)
            return resp
    # fallback
    import random
    return random.choice(FALLBACKS)

# --- Routes ---
@app.route("/")
def index():
    init_db()
    info = {"lang": "ja", "db": DB_PATH}
    return render_template("index.html", info=info)

@app.route("/api/chat", methods=["POST"])
def api_chat():
    init_db()
    data = request.get_json(force=True)
    if not data or "message" not in data:
        return jsonify({"error": "missing message"}), 400
    msg = data["message"].strip()
    if not msg:
        return jsonify({"error": "empty message"}), 400

    db = get_db()
    ts = time.time()
    cur = db.cursor()
    cur.execute("INSERT INTO messages (role, text, created_at) VALUES (?, ?, ?)", ("user", msg, ts))
    db.commit()

    reply = bot_response(msg)

    cur.execute("INSERT INTO messages (role, text, created_at) VALUES (?, ?, ?)", ("bot", reply, time.time()))
    db.commit()

    return jsonify({"reply": reply})

@app.route("/api/logs", methods=["GET"])
def api_logs():
    init_db()
    limit = int(request.args.get("limit", 200))
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, role, text, created_at FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    data = [{"id": r["id"], "role": r["role"], "text": r["text"], "created_at": r["created_at"]} for r in rows]
    return jsonify(data)

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
