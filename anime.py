from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote_plus
from colorama import Fore, Style, init
import time
import sys
from itertools import cycle
from selenium.webdriver.chrome.service import Service
import os
from selenium.common.exceptions import NoSuchDriverException
import base64
import subprocess
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import requests

# Initialize colorama
init(autoreset=True)

# Set up browser
chrome_options = Options()
chrome_options.add_argument("--log-level=3")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--headless=new")  # New headless mode
chrome_options.add_argument("--blink-settings=imagesEnabled=false")  # Disable images
chrome_options.add_argument("--disable-gpu")  # GPU hardware acceleration
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")  # Only if running as root
chrome_options.add_argument("--disable-software-rasterizer")
chrome_options.page_load_strategy = 'eager'  # Don't wait for full page load

# Add these experimental preferences
chrome_options.add_experimental_option("prefs", {
    "profile.managed_default_content_settings.images": 2,  # Disable images
    "profile.default_content_setting_values.javascript": 1,  # Keep JS enabled
    "profile.managed_default_content_settings.stylesheets": 2,  # Disable CSS
})

try:
    # Initialize driver
    chrome_service = Service(
        executable_path=r"C:\Users\joyboy\Desktop\project 2\chromedriver-win64\chromedriver.exe",
        log_output=os.devnull
    )
    driver = webdriver.Chrome(
        service=chrome_service, 
        options=chrome_options,
    )
except NoSuchDriverException:
    print(f"\n{Fore.RED}✖ ChromeDriver not found! Please follow these steps:")
    print(f"{Fore.YELLOW}1. Download ChromeDriver from: https://chromedriver.chromium.org/")
    print(f"2. Extract the executable and place it in:")
    print(f"   - Current directory: {os.getcwd()}")
    print(f"   - OR in system PATH (e.g.: C:\\Windows\\)")
    print(f"3. Ensure version matches your Chrome browser ({Fore.CYAN}Check Chrome version: chrome://settings/help{Fore.YELLOW})")
    print(f"{Style.RESET_ALL}")
    sys.exit(1)

def loading_animation():
    frames = cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    for _ in range(30):
        sys.stdout.write('\r' + Fore.BLUE + next(frames) + ' Loading...')
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\r' + ' ' * 30 + '\r')

def optimized_get(driver, url):
    """Faster page navigation using JavaScript"""
    driver.execute_script(f"window.location.href = '{url}';")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, 'body'))
    )

def fetch_episodes(driver, anime_url):
    """Optimized episode fetching with batch processing"""
    try:
        optimized_get(driver, anime_url)
        
        # Efficient scroll to load all episodes
        driver.execute_script("""
            let scrollCount = 0;
            const scrollInterval = setInterval(() => {
                window.scrollTo(0, document.body.scrollHeight);
                scrollCount++;
                if(scrollCount > 5) clearInterval(scrollInterval);
            }, 500);
        """)
        time.sleep(2)  # Allow time for content loading
        
        return driver.execute_script("""
            return Array.from(document.querySelectorAll('.episodes-card'))
                .map(card => ({
                    number: parseInt(card.querySelector('h3').innerText.match(/\\d+/)?.[0] || 0),
                    url: atob(card.querySelector('a[onclick]').getAttribute('onclick').split("'")[1])
                }))
                .filter(ep => ep.number > 0)
                .sort((a, b) => a.number - b.number);
        """)
    except Exception as e:
        print(f"{Fore.RED}⚠ Error fetching episodes: {e}{Style.RESET_ALL}")
        return []

def display_episodes(episodes, per_row=10):
    if not episodes:
        return
        
    max_num = episodes[-1]['number']
    num_width = len(str(max_num))
    total_rows = -(-len(episodes) // per_row)  # Ceiling division
    
    print(f"\n{Fore.CYAN}★ {Style.BRIGHT}Episodes List ({len(episodes)} total) ★{Style.RESET_ALL}")
    for i in range(total_rows):
        row = episodes[i*per_row : (i+1)*per_row]
        formatted = [f"{Fore.YELLOW}{ep['number']:{num_width}d}{Style.RESET_ALL}" for ep in row]
        print("  ".join(formatted))

def display_grid(items, start, end, per_row=5):
    current = items[start:end]
    max_len = len(str(current[-1]['number'])) if current else 0
    for i in range(0, len(current), per_row):
        row = [f"{Fore.YELLOW}{str(x['number']).rjust(max_len)}" for x in current[i:i+per_row]]
        print("  │  ".join(row))

def get_mediafire_link(driver):
    """Efficient mediafire link extraction"""
    try:
        original_window = driver.current_window_handle
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "mediafire")]/ancestor::a'))
        )
        driver.execute_script("arguments[0].click();", btn)
        
        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
        driver.switch_to.window([w for w in driver.window_handles if w != original_window][0])
        
        mediafire_url = driver.current_url
        driver.close()
        driver.switch_to.window(original_window)
        return mediafire_url
    except Exception as e:
        print(f"{Fore.RED}⚠ Mediafire link error: {e}{Style.RESET_ALL}")
        return None

def clear_network_cache(driver):
    driver.execute_cdp_cmd('Network.clearBrowserCache', {})
    
def clear_memory(driver):
    driver.execute_script("""
        window.stop();
        document.body.innerHTML = '';
        if(window.performance && window.performance.memory){
            window.performance.memory = null;
        }
    """)

def batch_process_episodes(episodes, batch_size=50):
    with ThreadPoolExecutor() as executor:
        return list(executor.map(process_episode, episodes))

def download_with_progress(url, filename):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    progress_bar = tqdm(
        total=total_size,
        unit='B',
        unit_scale=True,
        desc=f"{Fore.CYAN}⬇ {filename}",
        bar_format="{l_bar}{bar:40}{r_bar}",
        colour='GREEN'
    )
    
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(1024):
            f.write(chunk)
            progress_bar.update(len(chunk))
    
    progress_bar.close()
    print(f"{Fore.GREEN}✔ Download complete: {filename}{Style.RESET_ALL}")

def download_file(url, destination):
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        progress_bar = tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            desc=f"{Fore.MAGENTA}⏳ Downloading",
            bar_format=f"{Fore.YELLOW}{{l_bar}}{Fore.CYAN}{{bar:40}}{Fore.YELLOW}{{r_bar}}",
            colour='green'
        )
        
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(1024):
                if chunk:
                    f.write(chunk)
                    progress_bar.update(len(chunk))
        
        progress_bar.close()
        print(f"\n{Fore.GREEN}✅ Download complete! {Fore.CYAN}{os.path.basename(destination)}{Style.RESET_ALL}")
        return True
    
    except Exception as e:
        print(f"\n{Fore.RED}❌ Download failed: {str(e)}{Style.RESET_ALL}")
        return False

def main():
    try:
        # Get search query
        print(Fore.CYAN + "\n" + "="*50)
        print(f"{Fore.CYAN}★ {Style.BRIGHT}Anime Search Tool ★{Style.RESET_ALL}")
        print("="*50 + Style.RESET_ALL)
        anime_name = input(f"{Fore.YELLOW}➤ Enter anime name to search: {Style.RESET_ALL}").strip()
        
        # Format search query
        search_query = quote_plus(anime_name)
        search_url = f"https://witanime.cyou/?search_param=animes&s={search_query}"
        
        # Navigate to results
        print(f"\n{Fore.BLUE}⌛ Searching for {Style.BRIGHT}'{anime_name}'{Style.RESET_ALL}")
        loading_animation()
        optimized_get(driver, search_url)
        
        # Wait for results
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'anime-card-container'))
        )
        
        # Collect results
        results = driver.find_elements(By.CLASS_NAME, 'anime-card-container')
        
        if not results:
            print(f"\n{Fore.RED}✖ No results found{Style.RESET_ALL}")
            sys.exit()
        
        # Display results
        print(f"\n{Fore.CYAN}★ {Style.BRIGHT}Found {len(results)} results ★{Style.RESET_ALL}")
        for idx, result in enumerate(results, 1):
            title_element = result.find_element(By.XPATH, './/div[@class="anime-card-title"]//h3/a')
            title = title_element.text
            print(f"{Fore.YELLOW}{idx:2d}. {Fore.GREEN}{title}{Style.RESET_ALL}")
        
        # Get selection
        selection = int(input(f"\n{Fore.MAGENTA}➤ Enter choice number (1-{len(results)}): {Style.RESET_ALL}")) - 1
        selected_anime = results[selection]
        
        # Get link
        anime_link = selected_anime.find_element(By.XPATH, './/div[@class="anime-card-title"]//h3/a').get_attribute('href')
        print(f"\n{Fore.CYAN}★ {Style.BRIGHT}Selected anime page ★{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Style.BRIGHT}{anime_link}{Style.RESET_ALL}")

        # Add after getting anime_link
        print(f"\n{Fore.CYAN}⌛ Fetching episodes...")
        loading_animation()
        episodes = fetch_episodes(driver, anime_link)
        if not episodes:
            print(f"{Fore.RED}✖ No episodes found{Style.RESET_ALL}")
            sys.exit()

        # Display episodes with pagination
        if episodes:
            print(f"\n{Fore.CYAN}★ {Style.BRIGHT}Found {len(episodes)} episodes ★{Style.RESET_ALL}")
            display_episodes(episodes)
            try:
                ep_choice = int(input(f"\n{Fore.MAGENTA}➤ Enter episode number (1-{len(episodes)}): {Style.RESET_ALL}"))
                selected_url = episodes[ep_choice-1]['url']
            except (ValueError, IndexError):
                print(f"{Fore.RED}⚠ Invalid episode number{Style.RESET_ALL}")
                sys.exit()

        # Navigate to episode
        print(f"\n{Fore.CYAN}★ {Style.BRIGHT}Loading episode... ★{Style.RESET_ALL}")
        try:
            optimized_get(driver, selected_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            print(f"{Fore.GREEN}✔ Episode loaded successfully!{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}⚠ Failed to load episode: {e}{Style.RESET_ALL}")

        # Get MediaFire link
        mediafire_url = get_mediafire_link(driver)
        if mediafire_url:
            print(f"\n{Fore.CYAN}★ {Style.BRIGHT}MediaFire URL: {Style.BRIGHT}{mediafire_url}{Style.RESET_ALL}")
            
            # Close browser immediately after getting URL
            print(f"\n{Fore.RED}⚠ Closing browser...{Style.RESET_ALL}")
            driver.quit()
            
            download = input(f"\n{Fore.MAGENTA}➤ Download this file? (y/n): {Style.RESET_ALL}").strip().lower()
            
            if download == 'y':
                download_dir = os.path.join(os.getcwd(), "downloaded")
                os.makedirs(download_dir, exist_ok=True)
                
                try:
                    subprocess.run(
                        ["python", "mediafire.py", mediafire_url, "-o", download_dir],
                        check=True,
                        stdout=sys.stdout,  # Directly pipe output
                        stderr=sys.stderr,
                        text=True
                    )
                    print(f"\n{Fore.GREEN}✨ All done! Enjoy your anime! {Style.RESET_ALL}")
                except subprocess.CalledProcessError:
                    print(f"\n{Fore.RED}⚠ Download failed{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✖ MediaFire link not found{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}⚠ Critical error: {e}{Style.RESET_ALL}")
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    main()
