import time
import os
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse


url = "https://tv.apple.com/"

# Setup Chrome Options

chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


# Remove zero-width spaces and normalize whitespace

def clean_text(text):
    if not text: return "NA"
    text = text.replace('\u200b', '')
    return re.sub(r'\s+', ' ', text).strip()

def run_apple_tv(driver) :
    try:
        print(f"Navigating to {url}...")
        driver.get(url)
        time.sleep(5)

        # Scroling : we must scroll to the bottom to find the FAQ.
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Just to be safe, wait a moment for the DOM to settle
        time.sleep(3)

        # extraction of the site name from the URL
        site_name = urlparse(url).netloc.replace("www.", "").split(".")[0].capitalize()
        data = []
 
        # Updated Selector based on your HTML snippet:
        # The FAQ is inside <section data-testid="section-faq">
        # Each item is a <details> tag.
        faq_section = driver.find_element(By.XPATH, "//section[@data-testid='section-faq']")
        questions_elements = faq_section.find_elements(By.TAG_NAME, "details")


        print(f"Found {len(questions_elements)} FAQ items. Processing...")

        main_window = driver.current_window_handle

        for index, detail_el in enumerate(questions_elements):
            try:
                # Extract Question from the <summary> tag
                summary = detail_el.find_element(By.TAG_NAME, "summary")
                question_text = clean_text(summary.text)

                print(f"Processing ({index+1}): {question_text[:40]}...")

                #Expand the answer if not open (HTML5 <details> has an 'open' attribute)
                if not detail_el.get_attribute("open"):
                    driver.execute_script("arguments[0].click();", summary)
                    time.sleep(0.5) # Short wait for expansion

                # Extract Answer from the paragraph with class 'content'

                answer_el = detail_el.find_element(By.XPATH, ".//p[contains(@class, 'content')]")
                answer_text = clean_text(answer_el.text)

                #Extract Links Info
                links = answer_el.find_elements(By.TAG_NAME, "a")
                link_names_temp = []
                linked_titles_temp = []

                for link in links:
                    try:
                        href = link.get_attribute("href")
                        l_text = clean_text(link.text)

                        if href and href.startswith("http"):
                            link_names_temp.append(l_text if l_text else "Icon/Image Link")

                            # Open the link in a new tab to fetch its actual Page Title

                            driver.execute_script("window.open(arguments[0]);", href)
                            driver.switch_to.window(driver.window_handles[-1])

                            # Wait for title to load
                            try:
                                WebDriverWait(driver, 10).until(lambda d: d.title != "")
                                page_title = driver.title.strip()

                            except:
                                page_title = "Title Timeout/Error"

                           

                            linked_titles_temp.append(page_title)

                            # Close the sub-tab and switch focus back to the main FAQ page

                            driver.close()
                            driver.switch_to.window(main_window)

                    except Exception as e:
                        print(f"  Warning: Could not process a link. Error: {e}")
                        continue

 

                #Prepare Row Data

                row = {
                    "site_name": site_name,
                    "url": url,
                    "question": question_text,
                    "answer": answer_text,
                    "category": "NA", # No category
                    "internal_link": 1 if linked_titles_temp else 0,
                    "link_name": ", ".join(link_names_temp) if link_names_temp else "NA",
                    "linked_page_title": ", ".join(linked_titles_temp) if linked_titles_temp else "NA"
                }
                data.append(row)

            except Exception as e:
                print(f"Error extracting question {index+1}: {e}")
                continue

    except Exception as e:
        print(f"Global error or FAQ section not found: {e}")

    print(f"-- Finished Apple TV FAQ Scrapping ({len(data)} rows) ---")
    return pd.DataFrame(data)

 