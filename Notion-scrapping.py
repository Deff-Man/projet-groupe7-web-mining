import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from deep_translator import GoogleTranslator

# Main URL to start scraping
MAIN_URL = "https://www.notion.com/templates/category/faqs"
SITE_NAME = "Notion"
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
def get_answer(driver, question_element):
    try:
        # Try clicking the question in case the answer is hidden (accordion)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", question_element)

        parent_details = question_element.find_element(By.XPATH, "./..")
        
        is_open = parent_details.get_attribute("open")
        if is_open is None: 
            driver.execute_script("arguments[0].click();", question_element)
            time.sleep(0.5)
            
        return parent_details
    except:
        return None

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
        time.sleep(4)

    try:
        # Accept cookies if the popup appears
        try:
            driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
        except:
            pass

       # Scroll to load dynamic content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)

        # Find all possible question elements 
        questions_elements = driver.find_elements(By.TAG_NAME, "summary")
        if not questions_elements:
            questions_elements = driver.find_elements(By.XPATH, "//h2 | //h3 | //button")

        for q in questions_elements:
            q_text_raw = clean_text(q)

            # Filter out non-questions or duplicates
            if "?" not in q_text_raw or len(q_text_raw) < 10 or q_text_raw in seen_questions:
                continue
            seen_questions.add(q_text_raw)

            # Category
            category = "NA"
            try:
                # Find the closest H2 (direct category) and H1 (super category)
                direct_cat = q.find_elements(By.XPATH, "preceding::h2[1]")
                super_cat = q.find_elements(By.XPATH, "preceding::h1[1]")
                
                titles = []
                forbidden_phrases = ["faq", "frequently asked questions"]

                if super_cat:
                    s_txt = clean_text(super_cat[0])
                    if not any(phrase in s_txt.lower() for phrase in forbidden_phrases) and "sap" not in s_txt.lower():
                        titles.append(s_txt)

                if direct_cat:
                    d_txt = clean_text(direct_cat[0])
                    if not any(phrase in d_txt.lower() for phrase in forbidden_phrases) and d_txt not in titles:
                        titles.append(d_txt)
                
                category = translate(", ".join(titles)) if titles else "NA"
            except:
                category = "NA"

            # Answer extraction
            answer_container = get_answer(driver, q)
            if answer_container:
                full_txt = clean_text(answer_container)
                ans_raw = full_txt.replace(q_text_raw, "").strip()
                answer = translate(ans_raw)
            else:
                answer = "Content not found"

            # Links extraction
            links_urls = []
            links_names = [] 
            links_titles = []
            try:
                if answer_container:
                    anchors = answer_container.find_elements(By.TAG_NAME, "a")
                    for a in anchors:
                        href = a.get_attribute("href")
                        if href and "http" in href and href != url:
                            if href not in links_urls:
                                links_urls.append(href)
                                links_names.append(translate(clean_text(a)))
                                links_titles.append(get_link_title(driver, href))
                        if len(links_urls) >= 5: break
            except:
                pass

            # Joins multiple items with a comma
            def format_for_csv(items):
                return ", ".join(items) if items else "NA"

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
def run_notion(driver):
    
    data = []
    visited = set()
    seen_questions = set()

  
    # Load the main FAQ page
    driver.get(MAIN_URL)
    time.sleep(2)
        
    # Start scraping
    crawl(driver, MAIN_URL, 0, visited, seen_questions, data)

    print(f"-- Finished Notion FAQ Scrapping ({len(data)} rows) ---")
    return pd.DataFrame(data)

# Ce bloc permet de lancer le code si tu executes ce fichier directement
if __name__ == "__main__":
    # 1. Configuration du driver (nécessaire pour le test individuel)
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print("--- Début du test Notion ---")
        # 2. Appel de la fonction principale
        df_resultat = run_notion(driver)
        
        # 3. Affichage pour vérifier que ça fonctionne
        print("\nRésultats extraits :")
        print(df_resultat.head()) # Affiche les 5 premières lignes
        
    finally:
        driver.quit()