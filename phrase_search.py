import sqlite3

def format_timestamp(timestamp):
    """
    Converts a timestamp from HH:MM:SS.sss format to YouTube-compatible 3h6m58s format.
    Args:
        timestamp (str): Timestamp in HH:MM:SS.sss format.
    Returns:
        str: Timestamp in YouTube-compatible format.
    """
    hours, minutes, seconds = timestamp.split(":")
    seconds = seconds.split(".")[0]  # Remove milliseconds
    formatted = f"{int(hours)}h{int(minutes)}m{int(seconds)}s" if int(hours) > 0 else f"{int(minutes)}m{int(seconds)}s"
    return formatted

def search_phrase(phrase):
    """
    Searches for a phrase in the database and retrieves matching video links with timestamps.
    """
    conn = sqlite3.connect('phrase_search.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT videos.url, captions.timestamp 
        FROM captions
        JOIN videos ON captions.video_id = videos.video_id
        WHERE caption_text LIKE ?
    """, ('%' + phrase + '%',))
    results = cursor.fetchall()
    conn.close()
    return results

def main():
    print("Welcome to Phrase Search!")
    phrase = input("Enter a phrase to search for: ")
    results = search_phrase(phrase)

    if results:
        print(f"Found {len(results)} matches:")
        for url, timestamp in results:
            formatted_timestamp = format_timestamp(timestamp)
            print(f"{url}&t={formatted_timestamp}")
    else:
        print("No matches found.")

if __name__ == "__main__":
    main()
