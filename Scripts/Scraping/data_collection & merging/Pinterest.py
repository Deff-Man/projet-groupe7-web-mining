import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

base_url = "https://create.pinterest.com/fr/faq/"

#driver setup
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
# Disable notifications and popups for better script stability
chrome_options.add_argument("--disable-notifications") 

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
# Safety Measure: Set a global page load timeout to 20 seconds to prevent hanging
driver.set_page_load_timeout(20) 

#Standardizes text by removing newlines and collapsing multiple spaces.
def clean_text(text):
    if not text: return "NA"
    return " ".join(text.replace('\n', ' ').split())

#Attempts to retrieve the title of a linked page in a new tab. Designed with a fallback mechanism to ensure the main script doesn't crash on slow links
def get_linked_page_title(driver, url, main_window):
    if not url or "javascript" in url or url.startswith('#'): 
        return "Internal link/anchor"
    
    title = "Title not retrieved (External link)"
    try:
        # Open the link in a new tab 
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        
        # Give the page a moment to load metadata
        time.sleep(2) 
        title = driver.title.strip() if driver.title else "Untitled"
        
        # Close the tab and return focus to the main window
        driver.close()
        driver.switch_to.window(main_window)
    except Exception:
        # Recovery: Ensure the sub-tab is closed and focus returns to main window even on error
        try:
            if len(driver.window_handles) > 1:
                driver.close()
            driver.switch_to.window(main_window)
        except: pass
        title = "Page too slow or inaccessible"
    return title

#Main function to iterate through categories and accordion items.
def scrape_pinterest_final():
    url = "https://create.pinterest.com/fr/faq/"
    try:
        driver.get(url)
    except TimeoutException:
        print("Main page took too long, attempting to proceed anyway.")
    
    time.sleep(5)# Wait for React components to render
    main_window = driver.current_window_handle
    
    # Force a scroll to the bottom and back to top to trigger any lazy-loading content
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")

    data_list = []
    # Pinterest FAQ items are often inside 'BusinessAccordion' structures
    # We also target H2/H3 tags to identify Section Categories
    elements = driver.find_elements(By.XPATH, "//h2 | //h3 | //dl[contains(@class, 'BusinessAccordion')]")
    
    current_category = "General"
    
    for el in elements:
        # Case A: Element is a header, update the current category
        if el.tag_name in ['h2', 'h3']:
            current_category = el.text.strip()
            continue
        
        # Case B: Element is a Data List (Accordion container)
        if el.tag_name == 'dl':
            dts = el.find_elements(By.TAG_NAME, "dt")
            for dt in dts:
                try:
                    question_text = clean_text(dt.text)
                    if len(question_text) < 5: continue

                    # expand the accordion item
                    # Scroll the question into view and click via JS for better reliability
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dt)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", dt)
                    time.sleep(2) 

                    # answer :
                    # The answer is located in the immediately following 'dd' sibling tag
                    dd = dt.find_element(By.XPATH, "./following-sibling::dd[1]")
                    answer_text = clean_text(driver.execute_script("return arguments[0].innerText;", dd))

                    # Link informations
                    links_elements = dd.find_elements(By.TAG_NAME, "a")
                    has_link = 1 if links_elements else 0
                    names = []
                    titles = []

                    for link in links_elements:
                        l_text = link.text.strip()
                        l_url = link.get_attribute("href")
                        
                        if l_text and l_url:
                            names.append(l_text)
                            page_title = get_linked_page_title(driver, l_url, main_window)
                            titles.append(page_title)
                    
                    #Data storage
                    data_list.append({
                        "site_name": "Pinterest",
                        "url": url,
                        "question": question_text,
                        "answer": answer_text,
                        "category": current_category,
                        "internal_link": has_link,
                        "link_name": ", ".join(names) if names else "NA",
                        "linked_page_title": ", ".join(titles) if titles else "NA"
                    })

                    #Collapse the accordion
                    driver.execute_script("arguments[0].click();", dt)

                except Exception as e:
                    print(f"Error bypassed: {e}")
                    continue
    return pd.DataFrame(data_list)
