import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from deep_translator import GoogleTranslator

# Chrome_options
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080") 
    
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options) 
# Main URL to start scraping
MAIN_URL = "https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0063407"
SITE_NAME = "Zoom"
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
    if not element: return ""
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
def get_answer(driver, question_element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", question_element)
        time.sleep(0.3)
        # Try to locate the answer using the aria-labelledby attribute
        panel_id = question_element.get_attribute("aria-controls")
        if panel_id:
            if question_element.get_attribute("aria-expanded") == "false":
                driver.execute_script("arguments[0].click();", question_element)
                time.sleep(1.2)
            script_extract_accordion = f"""
                var panel = document.getElementById('{panel_id}');
                if (panel) {{
                    var content = panel.querySelector('.zm-collapse-item__content');
                    if (content) return content.innerText.trim();
                    return panel.innerText.trim();
                }}
                return "";
            """
            ans = driver.execute_script(script_extract_accordion)
            if ans and len(ans) > 5: return ans
        # Extraction logic for pricing pages
        script_pricing = """
            var header = arguments[0];
            var panel = header.nextElementSibling;
            if (!panel || !panel.classList.contains('zm-collapse-item__wrap')) {
                panel = header.parentElement.nextElementSibling;
            }
            if (panel) {
                var content = panel.querySelector('.zm-collapse-item__content');
                return content ? content.innerText.trim() : panel.innerText.trim();
            }
            return "";
        """
        ans_pricing = driver.execute_script(script_pricing, question_element)
        if ans_pricing and len(ans_pricing) > 5: return ans_pricing
        # Extraction logic using next siblings
        script_sibling = """
            var current = arguments[0];
            var textContent = "";
            var sib = current.nextElementSibling;
            while (sib && !['H1','H2','H3'].includes(sib.tagName)
                   && !sib.classList.contains('zm-collapse-item__header')
                   && !sib.classList.contains('zm-accordion__header')) {
                textContent += sib.innerText + " ";
                sib = sib.nextElementSibling;
            }
            return textContent.trim();
        """
        ans_sib = driver.execute_script(script_sibling, question_element)
        if ans_sib and len(ans_sib) > 5: return ans_sib
        return "Content not found"
    except Exception:
        return "Content not found"

# -- Recursive scraper --
def crawl(driver, url, depth, visited, seen_questions, rows):
    # Skip URL(s) that have already been visited
    if url in visited or depth > MAX_DEPTH:
        return
    visited.add(url)
    # Print to see current progress
    print(f"{'  '*depth}→ Scraping (depth {depth}): {url}")
    parent_window = driver.current_window_handle
    if depth > 0:
        # Open subpage in a new tab if depth > 0
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(6)
    try:
        # Accept cookies if the popup appears
        try:
            driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
        except: pass
        # Scroll to load dynamic content
        for _ in range(4):
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(0.5)
        # Find all possible question elements
        questions = driver.find_elements(By.CSS_SELECTOR, "h3, div.zm-collapse-item__header, button.zm-accordion__header, div.zm-accordion__header")
        for q in questions:
            q_text_raw = clean_text(q)
            # Filter out non-questions or duplicates
            if "?" not in q_text_raw or len(q_text_raw) < 10 or q_text_raw in seen_questions:
                continue
            seen_questions.add(q_text_raw)
            # Category extraction
            category = "NA"
            try:
                # Find the closest H2 (direct category) and H1 (super category)
                direct_cat = q.find_elements(By.XPATH, "preceding::h2[1]")
                super_cat = q.find_elements(By.XPATH, "preceding::h1[1]")
                titles = []
                forbidden_phrases = ["faq", "frequently asked questions"]
                if super_cat:
                    s_txt = clean_text(super_cat[0])
                    if not any(p in s_txt.lower() for p in forbidden_phrases) and "adobe acrobat" not in s_txt.lower():
                        titles.append(s_txt)
                if direct_cat:
                    d_txt = clean_text(direct_cat[0])
                    if not any(p in d_txt.lower() for p in forbidden_phrases) and d_txt not in titles:
                        titles.append(d_txt)
                category = translate(", ".join(titles)) if titles else "NA"
            except: category = "NA"
            # Answer extraction and translation
            raw_answer = get_answer(driver, q)
            answer = translate(raw_answer)
            # Links extraction
            links_urls, links_names, links_titles = [], [], []
            try:
                panel_id = q.get_attribute("aria-controls")
                answer_container = None
                if panel_id:
                    try: answer_container = driver.find_element(By.ID, panel_id)
                    except: pass
                if not answer_container:
                    potential_links = q.find_elements(By.XPATH, "following-sibling::*[position() <= 2]//a")
                else:
                    potential_links = answer_container.find_elements(By.TAG_NAME, "a")
                for a in potential_links:
                    href = a.get_attribute("href")
                    if href and "http" in href and href != url and href not in links_urls:
                        if "support.zoom.com" in href or "zoom.us" in href:
                            links_urls.append(href)
                            links_names.append(translate(clean_text(a)))
                            links_titles.append(get_link_title(driver, href))
                    if len(links_urls) >= 5: break
            except: pass
            
            # Format items for CSV
            def format_for_csv(items): return ", ".join(items) if items else "NA"
            # Save data
            rows.append({
                "site_name": SITE_NAME,
                "url": url,
                "question": translate(q_text_raw),
                "answer": answer,
                "category": category,
                "internal_link": 1 if links_urls else 0,
                "link_name": format_for_csv(links_names),
                "linked_page_title": format_for_csv(links_titles)
            })
            # Recursion
            if depth < MAX_DEPTH:
                for l_url in links_urls:
                    crawl(driver, l_url, depth + 1, visited, seen_questions, rows)
    finally:
        if depth > 0:
            driver.close()
            driver.switch_to.window(parent_window)

# -- MAIN --
def run_zoom(driver):
    
    data = []
    visited = set()
    seen_questions = set()

  
    # Load the main FAQ page
    driver.get(MAIN_URL)
    time.sleep(2)
        
    # Start scraping
    crawl(driver, MAIN_URL, 0, visited, seen_questions, data)

    print(f"-- Finished Zoom FAQ Scrapping ({len(data)} rows) ---")
    return pd.DataFrame(data)


