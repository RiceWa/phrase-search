from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3

app = Flask(__name__, static_folder='static')  # Serve frontend files from the 'static' directory
CORS(app)  # Enable CORS for all routes
DATABASE = 'phrase_search.db'  # SQLite database file

# Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    return conn

# Endpoint: Search for phrases in captions
@app.route('/search', methods=['GET'])
def search():
    phrase = request.args.get('q')  # Get the search query from the URL
    if not phrase:
        return jsonify({'error': 'Please provide a search query'}), 400

    # Log the received search phrase for debugging
    print(f"Search phrase received: {phrase}")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Query the database for matching captions
    cursor.execute(
        '''
        SELECT video_id, timestamp, caption_text
        FROM captions
        WHERE caption_text LIKE ?
        ''',
        ('%' + phrase + '%',)
    )
    results = cursor.fetchall()
    conn.close()

    # Format the results
    formatted_results = [
        {
            'video_id': row['video_id'],
            'timestamp': row['timestamp'],
            'caption_text': row['caption_text']
        }
        for row in results
    ]

    return jsonify({'results': formatted_results})

# Endpoint: Block an IP (for misuse tracking)
blocked_ips = set()

@app.before_request
def block_ips():
    ip = request.remote_addr
    if ip in blocked_ips:
        return jsonify({'error': 'Access denied'}), 403

@app.route('/block_ip', methods=['POST'])
def block_ip():
    ip = request.json.get('ip')
    if ip:
        blocked_ips.add(ip)
        return jsonify({'message': f'IP {ip} blocked'})
    return jsonify({'error': 'IP not provided'}), 400

# Serve the frontend HTML file
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True)
