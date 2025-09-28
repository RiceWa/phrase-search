import os
from googleapiclient.discovery import build

API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_video_links(api_key, channel_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # Fetch the Uploads Playlist ID
    response = youtube.channels().list(
        part='contentDetails',
        id=channel_id
    ).execute()

    if not response['items']:
        print("Invalid Channel ID. Please try again.")
        return []

    uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    # Fetch all video links from the playlist
    video_links = []
    next_page_token = None

    while True:
        playlist_response = youtube.playlistItems().list(
            part='snippet',
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        for item in playlist_response['items']:
            video_id = item['snippet']['resourceId']['videoId']
            video_links.append(f"https://www.youtube.com/watch?v={video_id}")

        next_page_token = playlist_response.get('nextPageToken')
        if not next_page_token:
            break

    return video_links

def save_to_file(video_links, file_name="video_urls.txt"):
    with open(file_name, 'w') as file:
        for link in video_links:
            file.write(link + '\n')
    print(f"Saved {len(video_links)} video links to {file_name}")

if __name__ == '__main__':
    print("Enter the YouTube Channel ID:")
    channel_id = input("> ").strip()

    video_links = get_video_links(API_KEY, channel_id)

    if video_links:
        save_to_file(video_links, 'video_urls.txt')
