import os
import subprocess
import time
import re
from urllib.parse import urlparse, parse_qs
from glob import glob

def video_id_from_url(url: str) -> str | None:
    # Works for watch?v=, youtu.be/, shorts/
    u = urlparse(url)
    if u.hostname in ("youtu.be", "www.youtu.be"):
        return u.path.strip("/").split("/")[0]
    if u.path.startswith("/shorts/"):
        return u.path.split("/")[2] if len(u.path.split("/")) > 2 else None
    qs = parse_qs(u.query)
    if "v" in qs:
        return qs["v"][0]
    # fallback: last path segment
    m = re.search(r"([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None

def vtt_exists(output_folder, vid):
    return bool(glob(os.path.join(output_folder, f"{vid}*.vtt")))

def try_one(url, output_folder, client=None, cookies_browser=None, sleep_after=0.2, impersonate=True):
    args = [
        "yt-dlp",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "en.*,en",
        "--convert-subs", "vtt",
        "--skip-download",
    ]

    # Add impersonation only if curl_cffi is installed
    if impersonate:
        try:
            import curl_cffi  # noqa: F401
            args += ["--impersonate", "chrome"]
        except Exception:
            pass  # no curl_cffi -> skip impersonation

    if client:
        args += ["--extractor-args", f"youtube:player_client={client}"]
    if cookies_browser:
        args += ["--cookies-from-browser", cookies_browser]

    args += ["-o", f"{output_folder}/%(id)s.%(ext)s", url]

    try:
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError as e:
        print(f"yt-dlp failed for client={client} cookies={cookies_browser}: {e}")

    time.sleep(sleep_after)



def download_vtt_files(url_file, output_folder, delay=0.2, cookies_browser=None):
    os.makedirs(output_folder, exist_ok=True)

    with open(url_file, 'r', encoding='utf-8') as f:
        urls = [u.strip() for u in f if u.strip()]

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Downloading captions for: {url}")
        vid = video_id_from_url(url)
        if not vid:
            print("  ! Could not parse video ID; skipping.")
            continue

        # 1) Preferred: android client (often fetches PO token)
        try_one(url, output_folder, client="android", cookies_browser=cookies_browser)
        if vtt_exists(output_folder, vid):
            time.sleep(delay); continue

        # 2) Fallback: ios client
        try_one(url, output_folder, client="ios", cookies_browser=cookies_browser)
        if vtt_exists(output_folder, vid):
            time.sleep(delay); continue

        # 3) Fallback: tv (or tv_embedded) client
        try_one(url, output_folder, client="tv_embedded", cookies_browser=cookies_browser)
        if vtt_exists(output_folder, vid):
            time.sleep(delay); continue

        # 4) Last resort: web client but with cookies from your browser session
        if not cookies_browser:
            print("  ! No English subs found. Consider passing cookies (chrome/firefox).")
        else:
            print("  ! No English subs even with cookies. This video may not have EN subs.")

        time.sleep(delay)

def main():
    url_file = "video_urls.txt"
    output_folder = "vtt_files"
    delay = 0.1

    # If you’re logged into YouTube in a browser, you can pass its cookies to improve subtitle access:
    # cookies_browser = "chrome"  # or "firefox", "chromium"
    cookies_browser = None

    download_vtt_files(url_file, output_folder, delay, cookies_browser=cookies_browser)
    print("Caption downloads completed!")

if __name__ == "__main__":
    main()
