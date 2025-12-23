import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# URL 
target_url = "https://asana.com/fr/faq"

FINAL_COLUMNS = ["site_name", "url", "question", "answer", "category", "internal_link", "link_name", "linked_page_title"]

#driver setup
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


#Normalizes text by removing newlines and collapsing multiple spaces.
def clean_text(text):
    if not text: return ""
    return " ".join(text.replace('\n', ' ').split())

#Opens a new tab to fetch the <title> of a linked page.
#Includes safety mechanisms to return to the main window even if the load fails.
def get_linked_page_title(driver, url, main_window):
    """ Ouvre un onglet pour récupérer le titre """
    title = "NA"
    try:
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(url)
        time.sleep(1) # Rapide car Asana charge vite
        title = driver.title.strip()
        driver.close()
        driver.switch_to.window(main_window)
    except:
        # Emergency recovery: ensure sub-tabs are closed and focus is returned
        try:
            if len(driver.window_handles) > 1: driver.close()
            driver.switch_to.window(main_window)
        except: pass
    return title

#Identifies all relevant links (<a> tags) within a specific HTML element.
#Filters for internal Asana links and excludes anchor hashes (#).
def extract_links_data(driver, element, main_window):
    """ Récupère les données des liens sans les ajouter au CSV tout de suite """
    links_data = []
    try:
        anchors = element.find_elements(By.TAG_NAME, "a")
        for a in anchors:
            href = a.get_attribute("href")
            txt = clean_text(a.text)
            
            # Filter logic: Must be an asana.com link, not an anchor, and must have text
            if href and "asana.com" in href and "#" not in href and txt:
                links_data.append({"url": href, "name": txt})
    except: pass
    return links_data


def scrape_asana(driver, url):
    driver.get(url)
    time.sleep(4)
    
    rows = []
    
    try:
        print(f"Analyzing page: {url}")

        # Locate the main content container. 
        # On Asana, FAQ content usually starts after the H1. 
        # We find the first H2 and target its parent container.
        try:
            first_h2 = driver.find_element(By.TAG_NAME, "h2")
            container = first_h2.find_element(By.XPATH, "./..")
        except:
            print("Structure not found, defaulting to body.")
            container = driver.find_element(By.TAG_NAME, "body")

        elements = container.find_elements(By.XPATH, "./*")
        
        #State variable
        last_seen_h2 = "NA"     # Memory for the current section title (Category)
        current_q = None        # Buffer for the active question
        current_cat = "NA"      # Buffer for the active category
        current_ans_parts = []  # List to store fragments of the answer
        current_links = []      # List to store links found within the answer
        
        main_window = driver.current_window_handle

        #Finalizes the current buffered question and answer.
        #Aggregates answer fragments and fetches page titles for discovered links.
        def save_question():
            nonlocal current_q, current_cat, current_ans_parts, current_links
            
            # Save only if a question exists AND it has content (prevents saving empty headers)
            if current_q and current_ans_parts:
                full_answer = " ".join(current_ans_parts)
                
                # Link Metadata Processing
                link_names = []
                link_titles = []
                has_link = 0
                
                # Remove duplicates 
                unique_links = {l['url']: l for l in current_links}.values()
                
                if unique_links:
                    has_link = 1
                    for l in unique_links:
                        link_names.append(l['name'])
                        # Fetch remote title now to avoid slowing down the initial DOM scan
                        t = get_linked_page_title(driver, l['url'], main_window)
                        link_titles.append(t)
                
                # Convert metadata lists to comma-separated strings
                str_link_names = ", ".join(link_names) if link_names else "NA"
                str_link_titles = ", ".join(link_titles) if link_titles else "NA"
                
                rows.append([
                    "Asana", url, current_q, full_answer, current_cat, 
                    has_link, str_link_names, str_link_titles
                ])
            
            # Reset buffers for the next question
            current_q = None
            current_cat = "NA"
            current_ans_parts = []
            current_links = []

        
        for el in elements:
            tag = el.tag_name.lower()
            text = clean_text(el.text)
            
            # CASE 1: Heading Level 2
            if tag == 'h2':
                save_question()     # Save previous question before starting new section
                
                last_seen_h2 = text # Set this H2 as the Category for upcoming H3s
                
                # Temporarily assume H2 might be a question (common in simpler FAQs)
                current_q = text
                current_cat = "NA" # Tu ne veux pas le H1, donc pas de catégorie au dessus du H2
                
            # CASE 2: Heading Level 3
            elif tag == 'h3':
                save_question() # Close H2 buffer (if it was just a header)
                
                current_q = text # Set H3 as the actual Question
                current_cat = last_seen_h2 # Assign the H2 as its Category
                
            # CASE 3: Content (Answer)
            else:
                if current_q: # If a question is currently active in the buffer
                    if text:
                        current_ans_parts.append(text)
                        # Scan for links within this specific content block
                        found = extract_links_data(driver, el, main_window)
                        current_links.extend(found)

        # Finalize the very last question on the page
        save_question()

    except Exception as e:
        print(f"Error: {e}")

    return rows

