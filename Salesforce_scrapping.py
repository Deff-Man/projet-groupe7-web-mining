import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from deep_translator import GoogleTranslator

# Main URL to start scraping
MAIN_URL = "https://www.salesforce.com/campaign/lightning/faq/"
SITE_NAME = "Salesforce"
# MAX_DEPTH : 1 = Main page + linked pages
MAX_DEPTH = 1


# -- Help functions --

# 0/ Translates text to English using deep_translator
def translate(text):
    if not text or text == "NA" or text == "Content not found":
        return text
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except Exception:
        return text


# 1/ Removes extra spaces from the text content of an element
def clean_text(element):
    return " ".join(element.get_attribute("textContent").split())


# 2/ Retrieves the H1 title of a linked page using a temporary browser tab
def get_link_title(driver, url):
    parent = driver.current_window_handle
    title = "NA"

    try:
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)
        raw_title = clean_text(driver.find_element(By.TAG_NAME, "h1"))
        title = translate(raw_title)
        driver.close()
    except:
        pass
    finally:
        driver.switch_to.window(parent)
    return title

# 3/ Finds and extracts the answer associated with a given question element
def get_answer(driver, question):
    # Try clicking the question in case the answer is hidden (accordion)
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", question)
        driver.execute_script("arguments[0].click();", question)
        time.sleep(0.4)
    except:
        pass

    # 1/ Look for a direct ID link (Aria/Data-target)
    try:
        target_id = question.get_attribute("href") or question.get_attribute("data-target")
        if not target_id:
            parent_a = question.find_elements(By.XPATH, "./ancestor::a[1]")
            if parent_a: target_id = parent_a[0].get_attribute("href")
        
        if target_id and "#" in target_id:
            actual_id = target_id.split("#")[-1]
            ans_box = driver.find_element(By.ID, actual_id)
            if len(clean_text(ans_box)) > 5: return ans_box
    except: pass

    # 2/Look within the closest isolated container (Blade/Accordion)
    try:
        container = question.find_element(By.XPATH, "./ancestor::*[contains(@class, 'blade') or contains(@class, 'accordion') or contains(@class, 'container')][1]")
        potential_desc = container.find_elements(By.XPATH, ".//*[contains(@class, 'description') or contains(@class, 'text') or contains(@class, 'content')]")
        for desc in potential_desc:
            txt = clean_text(desc)
            if len(txt) > 20 and txt not in clean_text(question): return desc
    except: pass

    # 3/Check immediate next sibling
    try:
        sibling = question.find_elements(By.XPATH, "following-sibling::*[1]")
        if sibling:
            txt = clean_text(sibling[0])
            if len(txt) > 15 and "?" not in txt: return sibling[0]
    except: pass

    # 4/ Fallback to the first following paragraph
    try:
        p_fallback = question.find_elements(By.XPATH, "./following::p[1]")
        if p_fallback:
            txt_p = clean_text(p_fallback[0])
            if len(txt_p) > 20 and "?" not in txt_p: return p_fallback[0]
    except: pass

    return None


# -- Recursive scraper --
def crawl(driver, url, depth, visited, seen_questions, rows):
    # Skip URL(s) that have already been visited or exceed depth
    if url in visited or depth > MAX_DEPTH:
        return
    visited.add(url)

    # Print to see current progress
    print(f"{'  '*depth}→ Scraping (depth {depth}): {url}")

    parent = driver.current_window_handle
    if depth > 0:
        # Open subpage in a new tab if depth > 0
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(4)


    try:
        # Accept cookies if the popup appears
        try:
            driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
        except:
            pass

        # Scroll to load dynamic content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(2)

        # Find all possible question elements
        questions = driver.find_elements(By.XPATH, "//h2 | //h3 | //h4 | //button | //a[contains(text(), '?')]")

        for q in questions:
            q_text = clean_text(q)

            # Filter out non-questions, duplicates, or links/tracking parameters
            if "?" not in q_text or len(q_text) < 10 or q_text.lower() in seen_questions or "http" in q_text:
                continue
            seen_questions.add(q_text.lower())
            
            # Category
            category = "General"
            try:
                # Find the closest H2 (direct category) and H1 (super category)
                super_cat = q.find_elements(By.XPATH, "preceding::h1[1]")
                direct_cat = q.find_elements(By.XPATH, "preceding::h2[1]")
                
                titles = []
                if super_cat: titles.append(clean_text(super_cat[0]))
                if direct_cat: titles.append(clean_text(direct_cat[0]))
                
                # Translate and join multiple categories
                category = translate(", ".join(titles)) if titles else "General"
            except:
                category = "General"
            
            # Answer extraction
            ans_el = get_answer(driver, q)
            answer = "Content not found"
            
            # Links extraction
            links_urls = []
            links_names = [] 
            links_titles = []

            if ans_el:
                answer = translate(clean_text(ans_el))
                try:
                    anchors = ans_el.find_elements(By.TAG_NAME, "a")
                    for a in anchors:
                        href = a.get_attribute("href")
                        # Ensure the link is valid and not the current page
                        if href and "http" in href and href.strip('/') != url.strip('/'):
                            links_urls.append(href)
                            links_names.append(translate(clean_text(a)))
                            
                            # Fetch the title of the linked page
                            links_titles.append(get_link_title(driver, href))
                        
                        if len(links_urls) >= 5:
                            break
                except:
                    pass

            # Joins multiple items with a comma for CSV
            def format_for_csv(items):
                if not items: 
                    return "NA"
                return ", ".join(items)

            # Save data
            rows.append({
                "site_name": SITE_NAME,
                "url": url,
                "question": translate(q_text),
                "answer": answer,
                "category": category,
                "internal_link": 1 if links_urls else 0,
                "link_name": format_for_csv(links_names), 
                "linked_page_title": format_for_csv(links_titles) 
            })

            # Recursion
            if depth < MAX_DEPTH:
                for l_url in links_urls:
                    if "salesforce.com" in l_url:
                        crawl(driver, l_url, depth + 1, visited, seen_questions, rows)

    finally:
        if depth > 0:
            driver.close()
            driver.switch_to.window(parent)


# -- MAIN --
def run_salesforce(driver):
    
    data = []
    visited = set()
    seen_questions = set()

  
    # Load the main FAQ page
    driver.get(MAIN_URL)
    time.sleep(2)
        
    # Start scraping
    crawl(driver, MAIN_URL, 0, visited, seen_questions, data)

    print(f"-- Finished Salesforce FAQ Scrapping ({len(data)} rows) ---")
    return pd.DataFrame(data)

