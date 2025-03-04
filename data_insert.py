import sqlite3

def create_tables():
    conn = sqlite3.connect('phrase_search.db')
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            url TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS captions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            timestamp TEXT,
            caption_text TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    """)
    conn.commit()
    conn.close()

def insert_data():
    conn = sqlite3.connect('phrase_search.db')
    cursor = conn.cursor()

    with open("parsed_captions.txt", "r", encoding="utf-8") as file:
        for line in file:
            video_id, timestamp, caption_text = line.strip().split("\t")
            cursor.execute("INSERT OR IGNORE INTO videos (video_id, url) VALUES (?, ?)", 
                           (video_id, f"https://www.youtube.com/watch?v={video_id}"))
            cursor.execute("INSERT INTO captions (video_id, timestamp, caption_text) VALUES (?, ?, ?)", 
                           (video_id, timestamp, caption_text))
    
    conn.commit()
    conn.close()

def main():
    create_tables()
    insert_data()
    print("Data insertion completed.")

if __name__ == "__main__":
    main()
