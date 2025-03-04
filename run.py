import os
import shutil
import datetime

def create_timestamped_backup_folder(parent_folder):
    """
    Creates a timestamped backup folder inside a parent folder.
    """
    os.makedirs(parent_folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = os.path.join(parent_folder, f"backup_{timestamp}")
    os.makedirs(backup_folder, exist_ok=True)
    return backup_folder

def ensure_vtt_folder():
    """
    Ensures the vtt_files folder exists.
    """
    folder_path = "vtt_files"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created folder: {folder_path}")
    else:
        print(f"Folder already exists: {folder_path}")

def move_file_to_backup(file_path, backup_folder):
    """
    Moves a file to the backup folder.
    """
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return
    os.makedirs(backup_folder, exist_ok=True)
    file_name = os.path.basename(file_path)
    destination_path = os.path.join(backup_folder, file_name)
    shutil.move(file_path, destination_path)
    print(f"Moved {file_name} to {backup_folder}.")

def move_folder_to_backup(folder_path, backup_folder):
    """
    Moves an entire folder to the backup folder.
    """
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} does not exist.")
        return
    os.makedirs(backup_folder, exist_ok=True)
    folder_name = os.path.basename(folder_path)
    destination_path = os.path.join(backup_folder, folder_name)
    shutil.move(folder_path, destination_path)
    print(f"Moved {folder_name} to {backup_folder}.")

def main():

    print("Starting!")

    os.system("python url_maker.py")
    print("Finished getting url's")

    print("Converting url to vtt files...")
    os.system("python download_captions.py")
    
    print("Ensuring vtt_files folder exists...")
    ensure_vtt_folder()

    print("Parsing caption files...")
    os.system("python file_parser.py")
    print("Inserting data into the database...")
    os.system("python data_insert.py")

    print("Creating timestamped backup folder in 'backups' directory...")
    parent_backup_folder = "backups"
    backup_folder = create_timestamped_backup_folder(parent_backup_folder)

    print("Moving files to backup...")
    move_file_to_backup("video_urls.txt", backup_folder)
    move_folder_to_backup("vtt_files", backup_folder)
    move_file_to_backup("parsed_captions.txt", backup_folder)

    print(f"Setup complete! All files moved to {backup_folder}.")
    print("You can now search for phrases using phrase_search.py.")

if __name__ == "__main__":
    main()
