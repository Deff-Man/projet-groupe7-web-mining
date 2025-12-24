import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# URL 
base_url = "https://www.airbnb.com/resources/hosting-homes/t/common-questions-23"

#driver setup
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--start-maximized")
# User agent to avoid being detected as a robot
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")

# driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

#Clean up the text: remove line breaks and multiple spaces
def clean_text(text):
    if not text: return ""

    return " ".join(text.replace('\n', ' ').split())

#Open a new tab to retrieve the link title 
def get_linked_page_title(driver, link_url):
    if not link_url.startswith("http"): return "Link not navigable"
    
    current_handle = driver.current_window_handle
    page_title = "Title not found"
    try:
        # Open a new tab and navigate to the link
        driver.switch_to.new_window('tab')
        driver.get(link_url)
        time.sleep(2.5) # Wait for the page to load
        page_title = driver.title.strip()
        driver.close()
        driver.switch_to.window(current_handle) # Switch focus back to the main list
    except:
        # Fallback to ensure we don't lose the main window reference in case of a crash
        try:
            driver.close()
            driver.switch_to.window(current_handle)
        except: pass
    
    return clean_text(page_title)

# Article discovery
#Scans the main landing page to extract a list of all article URLs and titles.
def get_articles_from_home(driver, main_url):
    driver.get(main_url)
    time.sleep(5) 
    
    articles_list = []
    try:
        # Locate article cards using an XPATH that targets URLs containing '/a/'
        elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/resources/hosting-homes/a/')]")
        
        for el in elements:
            url = el.get_attribute("href")
            # Text on the card is usually split into multiple lines
            full_text = el.text.split("\n")
            
            # The question is typically the first line (bold text) on the card
            if len(full_text) > 0:
                question = clean_text(full_text[0])
            else:
                question = "Unknown question"
            
            # Avoid duplicates
            if url and question and url not in [x['url'] for x in articles_list]:
                articles_list.append({"url": url, "question": question})
                
    except Exception as e:
        print(f"List error : {e}")
    
    print(f"{len(articles_list)} questions found.")
    return articles_list

#Article content extraction
def scrape_article_content(driver, article_data):
    url = article_data['url']
    question = article_data['question']
    
    print(f"Treatment : {question[:40]}...")
    
    try:
        driver.get(url)
        time.sleep(4) # Generous pause for content rendering

        #initialization
        category = "NA"
        full_answer = ""
        links_found = []

        try:
            # Target the primary <main> block to avoid header/footer noise
            main_block = driver.find_element(By.TAG_NAME, "main")
            
            # text extraction : Capture all visible text inside the main block
            raw_text = main_block.text
            # Remove the repeated question title from the start of the answer s'il est répété dedans
            full_answer = clean_text(raw_text.replace(question, ""))

            # Link extraction : Find all <a> tags within the main block
            all_links = main_block.find_elements(By.TAG_NAME, "a")
            
            
            for link in all_links:
                href = link.get_attribute("href")
                text = clean_text(link.text)
                
                #link filtering 
                #Skip empty links oe JS calls 
                if not href or "javascript" in href: continue
                
                #Skip Breadcrumb/Navigation links to keep only relevant article links
                if text in ["Home", "Hosting homes", "Resources", "Resource Center"]: continue
                
                # Skip Feedback buttons
                if "helpful" in text.lower(): continue
                
                # Add valid links if they have descriptive text and are unique
                if len(text) > 1:
                    if href not in [x['url'] for x in links_found]:
                        links_found.append({"url": href, "text": text})

        except Exception as e:
            full_answer = f"Error reading content: {e}"

        # Formating 
        internal_link = 1 if links_found else 0
        
        link_names_acc = []
        link_titles_acc = []
        
        # Process each filtered link found within the answer
        for l in links_found:
            link_names_acc.append(l['text'])
            ## CRAWL: Visit the link to get the remote page title
            t = get_linked_page_title(driver, l['url'])
            link_titles_acc.append(t)

        # Join lists into single strings for CSV compatibility
        link_name_str = ", ".join(link_names_acc) if link_names_acc else "NA"
        linked_page_title_str = ", ".join(link_titles_acc) if link_titles_acc else "NA"

        return {
            "site_name": "Airbnb FAQ",
            "url": url,
            "question": question,
            "answer": full_answer,
            "category": category,
            "internal_link": internal_link,
            "link_name": link_name_str,
            "linked_page_title": linked_page_title_str
        }

    except Exception as e:
        print(f"Technical error on {url}: {e}")
        return None

# FUNCTION TO CONNECT WITH MAIN.PY
def run_airbnb(driver):
    base_url = "https://www.airbnb.com/resources/hosting-homes/t/common-questions-23"
    
    # 1. Get the list of articles
    articles = get_articles_from_home(driver, base_url)
    
    results = []
    
    # 2. Scrape each article
    for art_data in articles:
        res = scrape_article_content(driver, art_data)
        if res:
            results.append(res)
            
    # 3. Return as DataFrame
    return pd.DataFrame(results)
