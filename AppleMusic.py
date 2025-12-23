import time
import pandas as pd
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse

url = "https://www.apple.com/fr/apple-music/"

#driver setup
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

#Nettoie une chaîne de caractères en supprimant les espaces superflus
def clean_text(text):
    if not text: return "NA"
    return re.sub(r'\s+', ' ', text).strip()

def run_apple_music(driver) :
    try :
        print(f"Opening: {url}")
        driver.get(url)
        time.sleep(5)
        
        # Scroll to bottom to ensure elements load 
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        #Site Name
        domain = urlparse(url).netloc
        site_name = domain.replace("www.", "").split(".")[0].capitalize() 

        data = []
        
        # Selectors for Apple FAQ - Apple structure often uses 'section-faq' class
        questions_elements = driver.find_elements(By.XPATH, "//section[contains(@class, 'section-faq')]//h3")
        
        # Filter out empty or hidden elements
        questions_elements = [q for q in questions_elements if len(q.text.strip()) > 5]
            
        main_window = driver.current_window_handle

        for index, q_element in enumerate(questions_elements):
            try:
                #question
                question_text = clean_text(q_element.text)
                print(f"Processing ({index+1}): {question_text[:30]}...")

                # open accordion
                # Locate parent LI to check state and find answer container
                list_item = q_element.find_element(By.XPATH, "./ancestor::li[1]")
                
                # Click if collapsed
                if "collapsed" in list_item.get_attribute("class") or "expanded" not in list_item.get_attribute("class"):
                    driver.execute_script("arguments[0].click();", q_element)
                    time.sleep(1) 

                # answer
                answer_element = list_item.find_element(By.XPATH, ".//div[contains(@class, 'accordion-content') or contains(@class, 'typography-body')]")
                
                # Get text via JS for better hidden text handling
                answer_raw = driver.execute_script("return arguments[0].textContent;", answer_element)
                answer_text = clean_text(answer_raw)

                #link information
                links = answer_element.find_elements(By.TAG_NAME, "a")
                
                link_anchor_texts = [] # What is written on the link (link_name)
                link_page_titles = []  # Title of the page it goes to (linked_page_title)
                
                for link in links:
                    try:
                        href = link.get_attribute("href")
                        anchor = clean_text(link.text)
                        
                        if href and href.startswith("http"):
                            # Store Anchor Text
                            link_anchor_texts.append(anchor if anchor else "Image/Icon Link")
                            
                            # Open in new tab to get Title
                            driver.execute_script("window.open(arguments[0]);", href)
                            driver.switch_to.window(driver.window_handles[-1])
                            
                            time.sleep(2) # Wait for page load
                            page_title = driver.title.strip()
                            link_page_titles.append(page_title if page_title else "No Title")
                            
                            # Close and return
                            driver.close()
                            driver.switch_to.window(main_window)
                    except Exception as e:
                        print(f"  Warning: Could not process a link. Error: {e}")
                        continue

                #SAVE ROW DATA
                row = {
                    "site_name": site_name,
                    "url": url,
                    "question": question_text,
                    "answer": answer_text,
                    "category": "NA", # No category
                    "internal_link": 1 if link_anchor_texts else 0,
                    # Join with commas as requested
                    "link_name": ", ".join(link_anchor_texts) if link_anchor_texts else "NA",
                    "linked_page_title": ", ".join(link_page_titles) if link_page_titles else "NA"
                }
                data.append(row)

            except Exception as e:
                print(f"Error on item {index}: {e}")
                continue
    except Exception as e:
        print(f"Global error: {e}")
    
    return pd.DataFrame(data)

