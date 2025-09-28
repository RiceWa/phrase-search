from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import psycopg
from psycopg_pool import ConnectionPool

# Serve frontend from /static (index.html)
app = Flask(__name__, static_folder='static')

# CORS (restrict in prod)
frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
CORS(app, resources={r"/*": {"origins": frontend_origin}})

# Neon/Postgres pool
DSN = os.getenv("DATABASE_URL")
if not DSN:
    raise RuntimeError("DATABASE_URL is not set")
pool = ConnectionPool(conninfo=DSN, min_size=0, max_size=5, timeout=45)

# health
@app.route("/healthz")
def healthz():
    try:
        with pool.connection() as conn:
            conn.execute("select 1")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

# /search?q=...&limit=20&offset=0
@app.route("/search", methods=["GET"])
def search():
    phrase = request.args.get("q", "").strip()
    limit = max(1, min(int(request.args.get("limit", 20)), 50))
    offset = max(0, int(request.args.get("offset", 0)))
    if not phrase:
        return jsonify({"error": "Please provide a search query"}), 400

    use_fts = len(phrase) >= 2 and any(ch.isalnum() for ch in phrase)

    with pool.connection() as conn, conn.cursor() as cur:
        if use_fts:
            sql = """
            SELECT c.video_id, c."timestamp", c.caption_text
            FROM captions c
            WHERE to_tsvector('english'::regconfig, c.caption_text)
                  @@ phraseto_tsquery('english'::regconfig, %(q)s)
            ORDER BY ts_rank(
                     to_tsvector('english'::regconfig, c.caption_text),
                     phraseto_tsquery('english'::regconfig, %(q)s)
                   ) DESC
            LIMIT %(limit)s OFFSET %(offset)s;
            """
            cur.execute(sql, {"q": phrase, "limit": limit, "offset": offset})
        else:
            # rare fallback for very short / non-alphanumeric inputs
            sql = """
            SELECT c.video_id, c."timestamp", c.caption_text
            FROM captions c
            WHERE c.caption_text ILIKE %(pat)s
            ORDER BY c."timestamp" ASC
            LIMIT %(limit)s OFFSET %(offset)s;
            """
            cur.execute(sql, {"pat": f"%{phrase}%", "limit": limit, "offset": offset})

        rows = cur.fetchall()

    results = [{"video_id": r[0], "timestamp": int(r[1]), "caption_text": r[2]} for r in rows]
    return jsonify({"results": results, "limit": limit, "offset": offset})

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    # Local dev: python app.py
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=True)
