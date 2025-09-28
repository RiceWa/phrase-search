from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from psycopg_pool import ConnectionPool

# --- App & CORS ---
app = Flask(__name__, static_folder="static")
frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
CORS(app, resources={r"/*": {"origins": frontend_origin}})

# --- DB Pool (create ONCE, after DSN is set) ---
DSN = os.getenv("DATABASE_URL")
if not DSN:
    raise RuntimeError("DATABASE_URL is not set")
# keep pool small on free tiers; short wait to borrow connections
pool = ConnectionPool(conninfo=DSN, min_size=0, max_size=3, timeout=10)

# --- Liveness: no dependencies; use this for Render health check ---
@app.route("/livez")
def livez():
    return {"ok": True, "version": os.getenv("RENDER_GIT_COMMIT", "")}

# --- Readiness: DB probe; never 5xx so the app page still loads ---
@app.route("/readyz")
def readyz():
    try:
        with pool.connection(timeout=5) as conn:
            conn.execute("SET LOCAL statement_timeout = 3000")  # 3s
            conn.execute("SELECT 1")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}, 200

# --- Optional: DB-backed health (manual use only) ---
@app.route("/healthz")
def healthz():
    try:
        with pool.connection(timeout=5) as conn:
            conn.execute("SET LOCAL statement_timeout = 3000")
            conn.execute("SELECT 1")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

# --- Search API ---
# Uses FTS with the SAME expression as your index:
#   to_tsvector('english'::regconfig, caption_text)
@app.route("/search", methods=["GET"])
def search():
    phrase = request.args.get("q", "").strip()
    limit = max(1, min(int(request.args.get("limit", 20)), 50))
    offset = max(0, int(request.args.get("offset", 0)))
    if not phrase:
        return jsonify({"error": "Please provide a search query"}), 400

    use_fts = len(phrase) >= 2 and any(ch.isalnum() for ch in phrase)

    try:
        with pool.connection(timeout=8) as conn, conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = 5000")  # 5s/query

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
                # fallback for very short / non-alphanumeric input
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

    except Exception as e:
        app.logger.exception("search failed")
        return jsonify({"error": "server_error", "detail": str(e)}), 500

# --- Static index ---
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

# --- Local dev entrypoint (Render uses gunicorn CMD from Dockerfile) ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=True)
