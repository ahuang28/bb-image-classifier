import selenium
import time
import os
import io
import hashlib
import requests
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

'''
# TEST
DRIVER_PATH = "C:/Users/Amy/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe"
chrome_options = Options()
chrome_options.add_argument('--proxy-server=http://127.0.0.1:7897')
wd = webdriver.Chrome(options=chrome_options)
#service = Service(DRIVER_PATH)
#wd = webdriver.Chrome(service=service)

#google site you are scraping
wd.get('https://google.com.hk/imghp') 
wait = WebDriverWait(wd, 10)
search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea.gLFyf')))
wait = WebDriverWait(wd, 5) 
search_box.send_keys('cats')
search_box.submit()
input("Press Enter to quit...")
#wd.quit()
'''

def fetch_image_urls(query: str, max_links_to_fetch: int, wd, sleep_between_interactions: int = 1):
    def scroll_to_end(wd):
        wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_between_interactions)

    # Build the Google Images query URL
    search_url = (
        "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp"
        "&q={q}&oq={q}&gs_l=img"
    )

    # Load the page
    wd.get(search_url.format(q=query))
    
    image_urls = set()
    image_count = 0
    results_start = 0

    while image_count < max_links_to_fetch:
        scroll_to_end(wd)

        # Get all image thumbnail results
        thumbnail_results = wd.find_elements(By.CSS_SELECTOR, "img.YQ4gaf")
        number_results = len(thumbnail_results)
        print(f"Found: {number_results} search results. Extracting links from {results_start}:{number_results}")

        for img in thumbnail_results[results_start:number_results]:
            try:
                # Filter out very small thumbnails (likely favicons or non-useful images)
                try:
                    h = int(img.get_attribute("height") or 0)
                    w = int(img.get_attribute("width") or 0)
                except Exception:
                    h, w = 0, 0
                if h < 50 or w < 50:
                    print("Skipping thumbnail because it's too small.")
                    continue

                # Scroll the thumbnail into view
                wd.execute_script("arguments[0].scrollIntoView(true);", img)
                # Wait until the element is visible and enabled
                WebDriverWait(wd, 10).until(lambda driver: img.is_displayed() and img.is_enabled())

                try:
                    img.click()
                except Exception as click_error:
                    print("Standard click failed, trying JavaScript click:", click_error)
                    # Attempt to remove/hide potential overlays interfering with the click
                    wd.execute_script("""
                        var overlays = document.querySelectorAll('div.CMgwv, div.lQHeM');
                        for (var i = 0; i < overlays.length; i++) {
                            overlays[i].style.display = 'none';
                        }
                    """)
                    # A brief pause to let the page update
                    time.sleep(0.5)
                    # Try JavaScript click again
                    wd.execute_script("arguments[0].click();", img)

                time.sleep(sleep_between_interactions)

            except Exception as e:
                print("Error clicking thumbnail:", e)
                continue

            # Wait for the full-size image to load and ensure its src starts with "http"
            try:
                valid_images = WebDriverWait(wd, 10).until(
                    lambda driver: [x for x in driver.find_elements(By.CSS_SELECTOR, "img[jsname='kn3ccd']") 
                                    if x.get_attribute("src") and x.get_attribute("src").startswith("http")]
                )
                for actual_image in valid_images:
                    src = actual_image.get_attribute("src")
                    if src:
                        image_urls.add(src)
                        print("Found image URL:", src)
            except Exception as e:
                print("Error waiting for full image URL:", e)

            image_count = len(image_urls)
            if image_count >= max_links_to_fetch:
                print(f"Found: {image_count} image links, done!")
                break

        # Update the start index for new thumbnails to avoid reprocessing
        if number_results > results_start:
            results_start = number_results
        else:
            # If no new thumbnails were loaded, break out of the loop.
            print("No more thumbnails found.")
            break

    return image_urls

def persist_image(folder_path: str, file_name: str, url: str):
    try:
        # Download the image with a timeout and error checking
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        image_content = response.content
    except Exception as e:
        print(f"ERROR - Could not download {url} - {e}")
        return

    try:
        # Open the image content with PIL
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file).convert("RGB")
        
        # Build the target folder path and create it if necessary
        target_folder = os.path.join(folder_path, file_name)
        os.makedirs(target_folder, exist_ok=True)
        
        # Generate a unique file name based on a hash of the content
        file_hash = hashlib.sha1(image_content).hexdigest()[:10] + '.jpg'
        file_path = os.path.join(target_folder, file_hash)
        
        # Save the image to disk
        with open(file_path, "wb") as f:
            image.save(f, "JPEG", quality=85)
        print(f"SUCCESS - saved {url} - as {file_path}")
    except Exception as e:
        print(f"ERROR - Could not save {url} - {e}")

if __name__ == '__main__':
    DRIVER_PATH = "C:/Users/Amy/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe"

    # Setup Chrome options if needed
    chrome_options = Options()
    chrome_options.add_argument('--proxy-server=http://127.0.0.1:7897')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument("--ignore-certificate-errors")
    
    # Create the service and initialize the webdriver
    service = Service(DRIVER_PATH)
    wd = webdriver.Chrome(service=service, options=chrome_options)
    #wd = webdriver.Chrome(options=chrome_options)

    queries = ["luka doncic", "lebron james", "stephen curry", "anthony davis", "kevin durant"]  # Change your set of queries here
    
    for query in queries:
        wd.get('https://google.com.hk/imghp')
        # Updated element lookup using By.CSS_SELECTOR
        #search_box = wd.find_element(By.CSS_SELECTOR, 'input.gLFyf')
        wait = WebDriverWait(wd, 10)
        search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea.gLFyf')))
        time.sleep(1) 
        search_box.send_keys(query)
        time.sleep(2)
        links = fetch_image_urls(query, 100, wd)
        
        # Change the image path below to your desired folder path
        images_path = "C:/Users/Amy/bb-image-classifier/model/dataset"
        for url in links:
            persist_image(images_path, query, url)
    
    wd.quit()
