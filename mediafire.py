#!/usr/bin/env python3

import hashlib
import http.client
import urllib.parse
from re import findall
from time import sleep
from io import BytesIO
from gzip import GzipFile
from requests import get
from gazpacho import Soup
from argparse import ArgumentParser
from os import path, makedirs, remove, chdir, getcwd
from threading import BoundedSemaphore, Thread, Event
from tqdm import tqdm
import time
import sys


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


# Non-alphanumeric (str.isalphanum()) characters allowed in a file or folder name
NON_ALPHANUM_FILE_OR_FOLDER_NAME_CHARACTERS = "-_. "
# What to replace bad characters with.
NON_ALPHANUM_FILE_OR_FOLDER_NAME_CHARACTER_REPLACEMENT = "-"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Accept-Encoding": "gzip",
}


def hash_file(filename: str) -> str:
    """
    Calculate the SHA-256 hash digest of a file.

    Args:
        filename (str): The path to the file.

    Returns:
        str: The hexadecimal representation of the hash digest.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        PermissionError: If the user does not have permission to read the file.
    """
    # make a hash object
    h = hashlib.sha256()

    # open file for reading in binary mode
    with open(filename, "rb") as file:
        # loop till the end of the file
        chunk = 0
        while chunk != b"":
            # read only 1024 bytes at a time
            chunk = file.read(1024)
            h.update(chunk)

    # return the hex representation of digest
    return h.hexdigest()


def normalize_file_or_folder_name(filename: str) -> str:
    """
    Normalize a file or folder name by replacing non-alphanumeric characters.

    Args:
        filename (str): The original file or folder name.

    Returns:
        str: The normalized file or folder name.

    Note:
        If you want to disable normalization, uncomment the return statement at the beginning of the function.

    Example:
        >>> normalize_file_or_folder_name("my_file$%")
        'my_file_'

    """
    return "".join(
        [
            (
                char
                if (
                    char.isalnum()
                    or char in NON_ALPHANUM_FILE_OR_FOLDER_NAME_CHARACTERS
                )
                else NON_ALPHANUM_FILE_OR_FOLDER_NAME_CHARACTER_REPLACEMENT
            )
            for char in filename
        ]
    )


def print_error(link: str):
    """
    Prints an error message indicating that a file has been deleted or blocked due to being dangerous.

    Parameters:
        link (str): The link to the file or resource that caused the error.

    Returns:
        None

    Example:
        >>> print_error("https://example.com/dangerous_file.txt")
        Deleted file or Dangerous File Blocked
        Take a look if you want to be sure: https://example.com/dangerous_file.txt
    """
    print(
        f"{bcolors.FAIL}Deleted file or Dangerous File Blocked\n"
        f"{bcolors.WARNING}Take a look if you want to be sure: {link}{bcolors.ENDC}"
    )


def main():
    """
    Mediafire Bulk Downloader

    Parses command-line arguments to download files or folders from Mediafire.

    Usage:
        python mediafire.py <mediafire_url> [-o <output_path>] [-t <num_threads>]

    Arguments:
        mediafire_url (str): The URL of the file or folder to be downloaded from Mediafire.

    Options:
        -o, --output (str): The path of the desired output folder. Default is the current directory.
        -t, --threads (int): Number of threads to use for downloading. Default is 10.

    Returns:
        None

    Example:
        To download a file:
        $ python mediafire.py https://www.mediafire.com/file/example_file.txt

        To download a folder:
        $ python mediafire.py https://www.mediafire.com/folder/example_folder -o /path/to/output -t 20
    """
    parser = ArgumentParser(
        "mediafire_bulk_downloader", usage="python mediafire.py <mediafire_url>"
    )
    parser.add_argument(
        "mediafire_url", help="The URL of the file or folder to be downloaded"
    )
    parser.add_argument(
        "-o",
        "--output",
        help="The path of the desired output folder",
        required=False,
        default=".",
    )
    parser.add_argument(
        "-t",
        "--threads",
        help="Number of threads to use",
        type=int,
        default=10,
        required=False,
    )

    args = parser.parse_args()

    folder_or_file = findall(
        r"mediafire\.com/(folder|file|file_premium)\/([a-zA-Z0-9]+)", args.mediafire_url
    )

    if not folder_or_file:
        print(f"{bcolors.FAIL}Invalid link{bcolors.ENDC}")
        exit(1)

    t, key = folder_or_file[0]

    if t in {"file", "file_premium"}:
        get_file(key, args.output)
    elif t == "folder":
        get_folders(key, args.output, args.threads, first=True)
    else:
        print(f"{bcolors.FAIL}Invalid link{bcolors.ENDC}")
        exit(1)

    print(f"{bcolors.OKGREEN}{bcolors.BOLD}All downloads completed{bcolors.ENDC}")
    exit(0)


def get_files_or_folders_api_endpoint(
    filefolder: str, folder_key: str, chunk: int = 1, info: bool = False
) -> str:
    """
    Constructs the API endpoint URL for retrieving files or folders information from Mediafire.

    Parameters:
        filefolder (str): Type of content to retrieve. Either 'file' or 'folder'.
        folder_key (str): The unique identifier of the folder.
        chunk (int): The chunk number to retrieve. Default is 1.
        info (bool): If True, gets folder info; otherwise, gets content. Default is False.

    Returns:
        str: The constructed API endpoint URL.

    Example:
        >>> get_files_or_folders_api_endpoint('folder', 'folder_key_123', chunk=2, info=True)
        'https://www.mediafire.com/api/1.4/folder/get_info.php?r=utga&content_type=folder&filter=all&order_by=name&order_direction=asc&chunk=2&version=1.5&folder_key=folder_key_123&response_format=json'
    """
    return (
        f"https://www.mediafire.com/api/1.4/folder"
        f"/{'get_info' if info else 'get_content'}.php?r=utga&content_type={filefolder}"
        f"&filter=all&order_by=name&order_direction=asc&chunk={chunk}"
        f"&version=1.5&folder_key={folder_key}&response_format=json"
    )


def get_info_endpoint(file_key: str) -> str:
    """
    Constructs the API endpoint URL for retrieving information about a specific file from Mediafire.

    Parameters:
        file_key (str): The unique identifier of the file.

    Returns:
        str: The constructed API endpoint URL.

    Example:
        >>> get_info_endpoint('file_key_123')
        'https://www.mediafire.com/api/file/get_info.php?quick_key=file_key_123&response_format=json'
    """
    return f"https://www.mediafire.com/api/file/get_info.php?quick_key={file_key}&response_format=json"


def get_folders(
    folder_key: str, folder_name: str, threads_num: int, first: bool = False
) -> None:
    """
    Recursively downloads folders and files from Mediafire.

    Parameters:
        folder_key (str): The unique identifier of the folder.
        folder_name (str): The name of the folder.
        threads_num (int): Number of threads to use for downloading.
        first (bool): If True, it's the first folder being processed. Default is False.

    Returns:
        None

    Example:
        >>> get_folders('folder_key_123', '/path/to/download', 5, first=True)
    """
    if first:
        r = get(get_files_or_folders_api_endpoint("folder", folder_key, info=True))
        if r.status_code != 200:
            message = r.json()["response"]["message"]
            print(f"{bcolors.FAIL}{message}{bcolors.ENDC}")
            exit(1)

        folder_name = path.join(
            folder_name,
            normalize_file_or_folder_name(r.json()["response"]["folder_info"]["name"]),
        )

    # If the folder doesn't exist, create and enter it
    if not path.exists(folder_name):
        makedirs(folder_name)
    chdir(folder_name)

    # Downloading all the files in the main folder
    download_folder(folder_key, threads_num)

    # Searching for other folders
    folder_content = get(
        get_files_or_folders_api_endpoint("folders", folder_key)
    ).json()["response"]["folder_content"]

    # Downloading other folders recursively
    if "folders" in folder_content:
        for folder in folder_content["folders"]:
            get_folders(folder["folderkey"], folder["name"], threads_num)
            chdir("..")


def download_folder(folder_key: str, threads_num: int) -> None:
    """
    Downloads all files from a Mediafire folder.

    Parameters:
        folder_key (str): The unique identifier of the folder.
        threads_num (int): Number of threads to use for downloading.

    Returns:
        None

    Example:
        >>> download_folder('folder_key_123', 5)
    """
    # Getting all the files
    data = []
    chunk = 1
    more_chunks = True

    try:
        # If there are more than 100 files, make another request
        # and append the result to data
        while more_chunks:
            r_json = get(
                get_files_or_folders_api_endpoint("files", folder_key, chunk=chunk)
            ).json()
            more_chunks = r_json["response"]["folder_content"]["more_chunks"] == "yes"
            data += r_json["response"]["folder_content"]["files"]
            chunk += 1

    except KeyError:
        print("Invalid link")
        return

    event = Event()
    threadLimiter = BoundedSemaphore(threads_num)
    total_threads: list[Thread] = []

    # Appending a new thread for downloading every link
    for file in data:
        total_threads.append(
            Thread(
                target=download_file,
                args=(
                    file,
                    event,
                    threadLimiter,
                ),
            )
        )

    # Starting all threads
    for thread in total_threads:
        thread.start()

    # Handle being interrupted
    try:
        while True:
            if all(not t.is_alive() for t in total_threads):
                break
            sleep(0.01)
    except KeyboardInterrupt:
        print(f"{bcolors.WARNING}Closing all threads{bcolors.ENDC}")
        event.set()
        for thread in total_threads:
            thread.join()
        print(f"{bcolors.WARNING}{bcolors.BOLD}Download interrupted{bcolors.ENDC}")
        exit(0)


def get_file(key: str, output_path: str = None) -> None:
    """
    Downloads a single file from Mediafire using the main thread.

    Parameters:
        key (str): The unique identifier of the file.
        output_path (str): The path where the file will be downloaded. If None, the current directory is used.

    Returns:
        None

    Example:
        >>> get_file('file_key_123', '/path/to/download')
    """
    # Retrieve file information
    file_data = get(get_info_endpoint(key)).json()["response"]["file_info"]

    # Change directory if output_path is provided
    if output_path:
        current_dir = getcwd()
        filename = path.join(output_path, file_data["filename"])
        chdir(output_path)
    else:
        filename = file_data["filename"]

    # Download the file
    download_file(file_data)

    if output_path:
        chdir(current_dir)
    return filename


def format_time(seconds: float) -> str:
    """Format seconds into hh:mm:ss or mm:ss"""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    elif minutes > 0:
        return f"{minutes}m {seconds:02d}s"
    else:
        return f"{seconds}s"


def download_file(
    file: dict, event: Event = None, limiter: BoundedSemaphore = None
) -> None:
    """Clean download progress with essential metrics"""
    try:
        download_link = file["links"]["normal_download"]
        filename = normalize_file_or_folder_name(file["filename"])
        
        if path.exists(filename) and hash_file(filename) == file["hash"]:
            print(f"{bcolors.WARNING}{filename}{bcolors.ENDC} exists, skipping")
            return

        # Get direct download URL
        parsed_url = urllib.parse.urlparse(download_link)
        conn = http.client.HTTPConnection(parsed_url.netloc)
        conn.request("GET", parsed_url.path, headers=HEADERS)
        response = conn.getresponse()

        if response.status >= 400:
            print_error(download_link)
            return

        # Handle redirects
        if 'content-disposition' not in response.headers:
            compressed_data = response.read()
            with GzipFile(fileobj=BytesIO(compressed_data)) as f:
                soup = Soup(f.read().decode("utf-8"))
                download_link = soup.find("a", {"id": "downloadButton"}).attrs["href"]
                parsed_url = urllib.parse.urlparse(download_link)
                conn = http.client.HTTPConnection(parsed_url.netloc)
                conn.request("GET", parsed_url.path, headers=HEADERS)
                response = conn.getresponse()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        start_time = time.time()
        last_update = 0
        
        print(f"\n{bcolors.HEADER}🚀 Downloading: {bcolors.OKBLUE}{filename}{bcolors.ENDC}")
        print(f"{bcolors.UNDERLINE}Total size: {total_size/1024/1024:.2f}MB{bcolors.ENDC}")

        with open(filename, 'wb') as f:
            while True:
                chunk = response.read(16384)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                
                # Update every 0.2 seconds to reduce flickering
                if time.time() - last_update < 0.2:
                    continue
                last_update = time.time()
                
                # Calculate metrics
                elapsed = time.time() - start_time
                percent = (downloaded / total_size) * 100
                speed = downloaded / elapsed / (1024*1024) if elapsed > 0 else 0
                eta = (total_size - downloaded) / (speed * 1024*1024) if speed > 0 else 0
                
                # Format ETA
                eta_str = format_time(eta) if speed > 0 else "--"
                speed_str = f"{speed:.2f}" if speed < 100 else f"{speed:.0f}"
                
                # Update display
                sys.stdout.write(f"\r{bcolors.OKGREEN}⏳ {percent:6.2f}%  "
                                f"{bcolors.OKCYAN}🚄 {speed_str:>5}MB/s  "
                                f"{bcolors.WARNING}⏱ {eta_str}{bcolors.ENDC}")
                sys.stdout.flush()

        # Final update to show 100%
        sys.stdout.write(f"\r{bcolors.OKGREEN}⏳ {100.00:6.2f}%  "
                        f"{bcolors.OKCYAN}🚄 {speed:.2f}MB/s  "
                        f"{bcolors.WARNING}⏱ 0s{bcolors.ENDC}")
        print(f"\n{bcolors.OKGREEN}✅ Download completed successfully!{bcolors.ENDC}")

    except Exception as e:
        print(f"\n{bcolors.FAIL}❌ Download failed: {str(e)}{bcolors.ENDC}")
    finally:
        conn.close()
        if limiter:
            limiter.release()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
