import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse


# URL FAQ Telegram
base_url = "https://telegram.org/faq" 

#driver setup
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--start-maximized")
# ANTI-BOT MEASURES: Mimic a real user and disable automation flags
chrome_options.add_argument("--disable-blink-features=AutomationControlled") 
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
# Optimization: 'eager' load strategy focuses on DOM availability
chrome_options.page_load_strategy = 'eager'

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.set_page_load_timeout(60)

#Normalizes text by removing newlines and extra spaces.
def clean_text(text):
    if not text: return ""
    return " ".join(text.replace('\n', ' ').split())

#Crawling: Opens a new tab to capture the HTML <title> of a linked page. Includes recovery logic to return focus to the main window.
def get_page_title(driver, url, main_window):
    
    title = "Title not found"
    try:
        driver.switch_to.new_window('tab')
        driver.get(url)
        time.sleep(1.5) # Wait for page metadata to load
        title = driver.title.strip()
        if not title: title = "Untitled"
        driver.close()
        driver.switch_to.window(main_window)
    except:
        # Emergency cleanup in case of tab crash or timeout
        try: 
            if len(driver.window_handles) > 1: driver.close()
            driver.switch_to.window(main_window)
        except: pass
    return title

#Finalizes an FAQ row by aggregating answer fragments and formatting link data. Organizes results into the requested CSV schema.
def save_entry(data_list, url, question, answer_parts, category, links_data):
    
    full_answer = " ".join(answer_parts)
    
    # Format metadata as comma-separated strings
    link_names_str = ", ".join([l['text'] for l in links_data]) if links_data else "NA"
    link_titles_str = ", ".join([l['title'] for l in links_data]) if links_data else "NA"
    
    # Extract domain as site name
    site_name = urlparse(url).netloc.replace("www.", "").split(".")[0].capitalize()

    if question and len(question) > 2:
        data_list.append({
            "site_name": site_name,
            "url": url,
            "question": question,
            "answer": full_answer,
            "category": category,
            "internal_link": 1 if links_data else 0,
            "link_name": link_names_str,       # Visible anchor text
            "linked_page_title": link_titles_str # Remote page HTML title
        })

def scrape_telegram_faq(driver, url, main_window):
    page_data = []
    
    try:
        driver.get(url)
    except:
        print("Load timeout, proceeding with existing DOM.")
        
    # --- HUMAN VERIFICATION PAUSE ---
    # Telegram/Cloudflare might trigger a CAPTCHA. This block pauses the script
    # to allow the developer to solve it manually before proceeding.
    print("\n" + "!"*60)
    print("🛑 SECURITY PAUSE")
    print("1. Solve any CAPTCHAs appearing in the browser.")
    print("2. Once the FAQ is visible, press ENTER below.")
    print("!"*60 + "\n")
    input(">>> Press ENTER to continue extraction...")
    
    try:
        # Locate the specific FAQ content container
        content_container = driver.find_element(By.ID, "dev_page_content")
        # Get all top-level children to parse them sequentially
        all_elements = content_container.find_elements(By.XPATH, "./*")
        
        # State Buffers
        current_category = "Général"
        current_question = "NA"
        current_answer_parts = []
        links_found = [] 

        for index, element in enumerate(all_elements):
            tag = element.tag_name.lower()
            text = clean_text(element.text)
            
            # Category detection (h3)
            if tag == 'h3':
                # Save previous buffered question before resetting for a new category
                if current_question != "NA":
                    save_entry(page_data, url, current_question, current_answer_parts, current_category, links_found)
                
                current_category = text
                current_question = "NA"
                current_answer_parts = []
                links_found = []
                
            #question detection (h4 or Bold Anchor)
            elif tag == 'h4' or (tag == 'b' and element.find_elements(By.XPATH, ".//a[@name]")):
                if current_question != "NA":
                    save_entry(page_data, url, current_question, current_answer_parts, current_category, links_found)
                
                # Cleanup: Telegram often prefixes questions with "Q:"
                if text.startswith("Q :") or text.startswith("Q:"):
                    parts = text.split(":", 1)
                    if len(parts) > 1:
                        text = parts[1].strip()
                
                current_question = text
                current_answer_parts = []
                links_found = []

            # Answer and link extraction
            elif tag in ['p', 'ul', 'ol', 'div', 'blockquote']:
                # Skip Table of Contents blocks
                if "toc" in element.get_attribute("class"): continue

                if current_question != "NA":
                    current_answer_parts.append(text)
                    
                    # Discover links within the current answer block
                    links = element.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        l_url = link.get_attribute("href")
                        l_text = clean_text(link.text) # On récupère le texte du lien (link_name)
                        
                        # Only process valid external/internal links (ignore anchor jumps)
                        if l_url and l_url.startswith("http") and "telegram.org/faq" not in l_url:
                            
                            if l_url not in [x['url'] for x in links_found]:
                                title = get_page_title(driver, l_url, main_window)
                                links_found.append({
                                    "url": l_url, 
                                    "text": l_text if l_text else "Lien", # link_name
                                    "title": title # linked_page_title
                                })

        # Save the final question found at the bottom of the page
        if current_question != "NA":
            save_entry(page_data, url, current_question, current_answer_parts, current_category, links_found)

    except Exception as e:
        print(f"Erreur globale : {e}")

    return page_data
