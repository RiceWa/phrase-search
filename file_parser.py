import os
import re
from datetime import timedelta

def clean_caption_text(text):
    """
    Cleans unwanted metadata and formatting from caption text.
    Args:
        text (str): Raw caption text.
    Returns:
        str: Cleaned caption text.
    """
    # Remove tags like '<00:00:00.539><c>' and other unwanted metadata
    text = re.sub(r'<.*?>', '', text).strip()

    # Remove placeholders like '[&nbsp;__&nbsp;]'
    text = re.sub(r'\[\s*(&nbsp;)*__(&nbsp;)*\s*\]', '', text)

    # Remove extra spaces
    return text.strip()

def parse_start_time(vtt_line):
    """
    Extracts the start time in seconds from a VTT timestamp line.
    Args:
        vtt_line (str): A line containing the VTT timestamp (e.g., "00:00:00.000 --> 00:00:02.450").
    Returns:
        float: Start time in seconds.
    """
    try:
        start_time = vtt_line.split("-->")[0].strip()
        parts = start_time.split(":")
        if len(parts) == 3:
            hours, minutes = map(float, parts[:2])
            seconds = float(parts[2].replace(".", ":").split(":")[0])
            return hours * 3600 + minutes * 60 + seconds
        else:
            raise ValueError(f"Invalid timestamp format: {start_time}")
    except Exception as e:
        print(f"Error parsing timestamp line: {vtt_line}, {e}")
        return 0.0  # Default to 0 seconds on error


def remove_duplicates(captions):
    """
    Removes duplicate captions by comparing their text and timestamps.

    Args:
        captions (list): List of tuples (timestamp, caption_text).
    Returns:
        list: List of unique captions.
    """
    unique_captions = []
    seen_texts = set()

    for timestamp, text in captions:
        if text not in seen_texts:
            unique_captions.append((timestamp, text))
            seen_texts.add(text)

    return unique_captions

def remove_redundant_captions(captions):
    """
    Removes captions with matching first four words between consecutive timestamps.

    Args:
        captions (list): List of tuples (timestamp, caption_text).
    Returns:
        list: List of filtered captions.
    """
    filtered_captions = []
    prev_text = None

    for timestamp, text in captions:
        # Get the first four words
        current_words = " ".join(text.split()[:4])
        prev_words = " ".join(prev_text.split()[:4]) if prev_text else None

        # Add to filtered list only if first 4 words differ
        if current_words != prev_words:
            filtered_captions.append((timestamp, text))
            prev_text = text

    return filtered_captions

def split_long_captions(captions, max_length=150, interval=1.0):
    """
    Splits captions that exceed the max_length into smaller segments and adjusts their timestamps.

    Args:
        captions (list): List of tuples (timestamp, caption_text).
        max_length (int): Maximum allowed length for a caption.
        interval (float): Time interval (in seconds) between split captions.
    Returns:
        list: List of split captions with adjusted timestamps.
    """
    split_captions = []
    
    for timestamp, text in captions:
        segments = []

        # Split the caption into smaller parts
        while len(text) > max_length:
            # Find the last punctuation within the max_length range
            split_point = max(
                text.rfind(punct, 0, max_length) for punct in ['.', '!', '?']
            )
            if split_point == -1:
                # If no punctuation is found, split at the nearest whitespace
                split_point = text.rfind(' ', 0, max_length)
            if split_point == -1:
                # If no whitespace is found, force split at max_length
                split_point = max_length
            
            # Append the segment and update the remaining text
            segments.append(text[:split_point + 1].strip())
            text = text[split_point + 1:].strip()

        # Append the remaining text
        segments.append(text)

        # Adjust timestamps for each segment
        for i, segment in enumerate(segments):
            adjusted_time = timestamp + (i * interval)
            split_captions.append((adjusted_time, segment))
    
    return split_captions

def merge_captions(captions, time_threshold=5):
    """
    Merges consecutive captions within a given time threshold.

    Args:
        captions (list): List of tuples (timestamp, caption_text).
        time_threshold (int): Max time difference (in seconds) to allow merging.
    Returns:
        list: List of merged captions.
    """
    merged = []
    if not captions:
        return merged

    current_timestamp, current_text = captions[0]

    for timestamp, text in captions[1:]:
        # Calculate time difference
        time_difference = timestamp - current_timestamp

        # Merge captions if time difference is within threshold
        if time_difference <= time_threshold:
            current_text = f"{current_text} {text}".strip()
        else:
            # Save the current caption and start a new one
            merged.append((current_timestamp, current_text))
            current_timestamp, current_text = timestamp, text

    # Add the last caption
    merged.append((current_timestamp, current_text))
    return merged

def parse_vtt_file(file_path):
    """
    Parses a .vtt file to extract captions and timestamps, filtering out non-speech elements.
    Args:
        file_path (str): Path to the .vtt file.
    Returns:
        list: A list of tuples (timestamp in seconds, cleaned caption text).
    """
    captions = []
    non_speech_tags = ['[Music]', '[Applause]', '[Laughter]', '[Sound]', '[Noise]']  # Add other tags if needed

    with open(file_path, 'r', encoding='utf-8') as file:
        # Skip the first three lines
        lines = file.readlines()[3:]

        timestamp = None
        text = []

        for line in lines:
            line = line.strip()

            # Match timestamp lines
            if "-->" in line:
                if timestamp and text:
                    # Store the previous caption
                    cleaned_text = clean_caption_text(' '.join(text))
                    if cleaned_text and not any(tag in cleaned_text for tag in non_speech_tags):
                        captions.append((timestamp, cleaned_text))
                    text = []
                # Extract the start time in seconds
                timestamp = parse_start_time(line)

            elif line:  # Non-empty lines are caption text
                text.append(line)

        # Handle the last caption
        if timestamp and text:
            cleaned_text = clean_caption_text(' '.join(text))
            if cleaned_text and not any(tag in cleaned_text for tag in non_speech_tags):
                captions.append((timestamp, cleaned_text))

    # Step 1: Remove duplicates
    unique_captions = remove_duplicates(captions)

    # Step 2: Remove redundant captions
    filtered_captions = remove_redundant_captions(unique_captions)

    # Step 3: Merge captions within 5-second periods
    merged_captions = merge_captions(filtered_captions, time_threshold=5)

    # Step 4: Split long captions
    return split_long_captions(merged_captions, max_length=150, interval=1.0)

def main():
    input_folder = "vtt_files"
    output_data = []

    if not os.path.exists(input_folder):
        print(f"Folder {input_folder} does not exist.")
        return

    for file_name in os.listdir(input_folder):
        if file_name.endswith(".vtt"):
            file_path = os.path.join(input_folder, file_name)
            video_id = file_name.split(".")[0]  # Extract video ID from file name
            captions = parse_vtt_file(file_path)
            output_data.append((video_id, captions))

    # Save data for insertion
    with open("parsed_captions.txt", "w", encoding="utf-8") as output_file:
        for video_id, captions in output_data:
            for timestamp, text in captions:
                output_file.write(f"{video_id}\t{int(timestamp)}\t{text}\n")

    print("Parsing completed. Data saved to parsed_captions.txt.")

if __name__ == "__main__":
    main()
