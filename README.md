# Anime Downloader Tool

This project consists of two Python scripts (`anime.py` and `mediafire.py`) that work together to search for anime episodes on [witanime.cyou](https://witanime.cyou) and download them from MediaFire.

## Features

### `anime.py`
- **Search Functionality**: Search for anime titles on witanime.cyou.
- **Episode Listing**: Display a list of episodes for the selected anime in a grid format.
- **MediaFire Integration**: Extract MediaFire download links for selected episodes.
- **Terminal UI**: Colored terminal output for better readability.
- **Performance Optimizations**: Headless browsing, disabled images/CSS, and efficient resource usage.
- **Error Handling**: Robust error handling for network issues, missing elements, and invalid inputs.

### `mediafire.py`
- **Bulk Downloader**: Download files or folders from MediaFire.
- **Threaded Downloads**: Supports multi-threaded downloads for faster performance.
- **Progress Tracking**: Displays download progress with speed, percentage, and ETA.
- **Error Handling**: Handles invalid links, deleted files, and dangerous file blocks.

## Prerequisites

- Python 3.8 or higher
- Google Chrome installed
- ChromeDriver (matching your Chrome version)
- Required Python packages (install via `pip install -r requirements.txt`)

## Setup

### Windows
1. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

2. **Download ChromeDriver**:
   - Download the correct version of ChromeDriver for your Chrome browser from [here](https://chromedriver.chromium.org/).
   - Alternatively, use the following PowerShell commands to download and install ChromeDriver automatically:
     ```powershell
     # Download the correct version
     irm https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.92/win64/chromedriver-win64.zip -OutFile chromedriver.zip

     # Extract to your project directory
     Expand-Archive -Path chromedriver.zip -DestinationPath "$env:USERPROFILE\Desktop\project 2"

     # Clean up
     del chromedriver.zip
     ```

3. **Run the Script**:
   ```powershell
   python anime.py
   ```

### Linux (APT-based distros)
1. **Install Dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-pip unzip
   pip install -r requirements.txt
   ```

2. **Install Google Chrome**:
   ```bash
   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
   sudo apt install ./google-chrome-stable_current_amd64.deb
   rm google-chrome-stable_current_amd64.deb
   ```

3. **Download ChromeDriver**:
   - Download the correct version of ChromeDriver for your Chrome browser from [here](https://chromedriver.chromium.org/).
   - Alternatively, use the following commands:
     ```bash
     # Download ChromeDriver
     wget https://chromedriver.storage.googleapis.com/$(curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip

     # Extract to your project directory
     unzip chromedriver_linux64.zip -d ~/Desktop/project\ 2

     # Clean up
     rm chromedriver_linux64.zip

     # Add to PATH
     export PATH=$PATH:~/Desktop/project\ 2
     ```

4. **Run the Script**:
   ```bash
   python3 anime.py
   ```

## Usage

1. **Search for Anime**:
   - Enter the anime name when prompted.
   - Select the desired anime from the search results.

2. **Select Episode**:
   - Choose an episode from the displayed list.

3. **Download**:
   - The script will extract the MediaFire link and prompt you to download the file.
   - Confirm the download to start the process.

## Example

```bash
python anime.py  # Windows
python3 anime.py  # Linux
```

Follow the on-screen instructions to search, select, and download anime episodes.

## Notes

- Ensure you have a stable internet connection for smooth downloads.
- For large files, consider using a download manager for better reliability.
- The script is optimized for performance but may take time for large downloads.

## Future Enhancements

- Configuration management for settings like download directory and threads.
- Quality selection for episodes.
- Batch downloads for multiple episodes. "# Arabic-Anime-Archive" 
