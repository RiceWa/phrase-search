# data_insert_pg.py
import os
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is not set")

pool = ConnectionPool(conninfo=DATABASE_URL, min_size=0, max_size=2, open=True)

def ensure_schema():
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS videos (
          video_id TEXT PRIMARY KEY,
          url TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS captions (
          id BIGSERIAL PRIMARY KEY,
          video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
          timestamp INTEGER NOT NULL,
          caption_text TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS captions_uniq
          ON captions (video_id, timestamp, caption_text);
        CREATE INDEX IF NOT EXISTS captions_caption_text_trgm_idx
          ON captions USING gin (caption_text gin_trgm_ops);
        CREATE INDEX IF NOT EXISTS captions_video_time_idx
          ON captions (video_id, timestamp);
        """)

def insert_data(parsed_file="parsed_captions.txt"):
    if not os.path.exists(parsed_file):
        raise SystemExit(f"{parsed_file} not found. Run file_parser.py first.")

    batch_vid, batch_cap = [], []
    BATCH = 2000

    def flush(cur):
        if batch_vid:
            cur.executemany(
                "INSERT INTO videos (video_id, url) VALUES (%s, %s) ON CONFLICT (video_id) DO NOTHING",
                batch_vid
            ); batch_vid.clear()
        if batch_cap:
            cur.executemany(
                "INSERT INTO captions (video_id, timestamp, caption_text) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                batch_cap
            ); batch_cap.clear()

    with pool.connection() as conn, conn.cursor() as cur, open(parsed_file, "r", encoding="utf-8") as f:
        for line in f:
            video_id, ts_str, text = line.rstrip("\n").split("\t", 2)
            batch_vid.append((video_id, f"https://www.youtube.com/watch?v={video_id}"))
            batch_cap.append((video_id, int(ts_str), text))
            if len(batch_cap) >= BATCH:
                flush(cur)
        flush(cur)

def main():
    ensure_schema()
    insert_data()
    print("Data insertion to Neon Postgres completed.")

if __name__ == "__main__":
    try:
        main()
    finally:
        # graceful pool shutdown to silence warnings
        try:
            pool.close()   # stop accepting new work
            pool.wait()    # wait for worker threads to stop
        except Exception:
            pass