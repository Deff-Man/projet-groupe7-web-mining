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


# URL
base_url = "https://proton.me/support/mail" 

#driver setup
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--start-maximized")

# Strategy 'eager': Selenium waits for the DOM but not all images/stylesheets
chrome_options.page_load_strategy = 'eager' 

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.set_page_load_timeout(60)

#Clean text by removing newlines and collapsing multiple spaces.
def clean_text(text):
    if not text: return "NA"
    return " ".join(text.replace('\n', ' ').split())

def run_ProtonMail(driver) : 
    try:
        print(f"Opening: {base_url}...")
        try:
            driver.get(base_url)
        except Exception as e:
            print("Initial load timeout ignored (Eager mode active).")
        
        # Wait explicitly for React/JS to render the buttons
        time.sleep(5)
        
        # Site Name
        domain = urlparse(base_url).netloc
        site_name = domain.replace("www.", "").split(".")[0].capitalize() # e.g. "Proton"
        
        data = []
        main_window_handle = driver.current_window_handle

        #Find FAQ Buttons
        # Proton uses buttons with div.rich-text inside for questions
        questions_buttons = driver.find_elements(By.XPATH, "//button[.//div[contains(@class, 'rich-text')]]")
        
        print(f"Found {len(questions_buttons)} FAQ buttons.")

        for index, btn in enumerate(questions_buttons):
            try:
                #Question
                question_el = btn.find_element(By.XPATH, ".//div[contains(@class, 'rich-text')]")
                question_text = clean_text(question_el.text)
                print(f"Processing ({index+1}): {question_text[:30]}...")

                #Open Accordion
                #Check 'aria-expanded' attribute
                if btn.get_attribute("aria-expanded") == "false":
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5) # Wait for animation

                # Answer 
                # The answer is in the element pointed to by 'aria-controls'
                panel_id = btn.get_attribute("aria-controls")
                answer_text = "NA"
                
                link_names_list = []
                link_titles_list = []

                if panel_id:
                    try:
                        panel = driver.find_element(By.ID, panel_id)
                        answer_text = clean_text(panel.text)
                        
                        # Links information
                        links = panel.find_elements(By.TAG_NAME, "a")
                        
                        for link in links:
                            href = link.get_attribute("href")
                            text = clean_text(link.text)
                            
                            if href and href.startswith("http"):
                                link_names_list.append(text if text else "Link")
                                
                                # Open new tab to get title
                                driver.execute_script("window.open(arguments[0]);", href)
                                driver.switch_to.window(driver.window_handles[-1])
                                
                                # Wait for title
                                time.sleep(2) 
                                page_title = driver.title.strip()
                                link_titles_list.append(page_title if page_title else "No Title")
                                
                                # Close the tab and go back to main FAQ page
                                driver.close()
                                driver.switch_to.window(main_window_handle)
                                
                    except Exception as e:
                        print(f"  > Panel error: {e}")

                #Data Storage 
                data.append({
                    "site_name": site_name,
                    "url": base_url,
                    "question": question_text,
                    "answer": answer_text,
                    "category": "Proton Mail FAQ", 
                    "internal_link": 1 if link_names_list else 0,
                    "link_name": ", ".join(link_names_list) if link_names_list else "NA",
                    "linked_page_title": ", ".join(link_titles_list) if link_titles_list else "NA"
                })

            except Exception as e:
                print(f"Error on question {index}: {e}")
                # Ensure we are on the main window if something crashed
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(main_window_handle)
                continue
    except Exception as e:
        print(f"Global error: {e}")
    return pd.DataFrame(data)

