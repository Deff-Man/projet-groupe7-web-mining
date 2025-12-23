import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
 
#Output folder and file path
OUTPUT_FOLDER = "/Users/matthieubeaumont/Desktop/Bureau/Projet_FAQ_web_mining/faq_scraper/faq_scraper/spiders"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "nvidia_faq.csv")
 
#Main URL to start scraping
MAIN_URL = "https://www.nvidia.com/en-us/geforce-now/faq/"
SITE_NAME = "NVIDIA"
#MAX_DEPTH : 1 = Main page + linked pages
MAX_DEPTH = 1
 
#Help functions
 
#1/ Removes extra spaces from the text content of an element
def clean_text(element):
    return " ".join(element.get_attribute("textContent").split())
 
#2/ Retrieves the H1 title of a linked page using a temporary browser tab
def get_link_title(driver, url):
    parent = driver.current_window_handle
    title = "NA"
 
    try:
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)
        title = clean_text(driver.find_element(By.TAG_NAME, "h1"))
        driver.close()
    except:
        pass
    finally:
        driver.switch_to.window(parent)
 
    return title
 
#3/ Finds and extracts the answer associated with a given question element
def get_answer(driver, question):
    #Try clicking the question in case the answer is hidden (accordion)
    try:
        driver.execute_script("arguments[0].click();", question)
        time.sleep(0.3)
    except:
        pass
 
    #Try to locate the answer using the aria-labelledby attribute
    try:
        qid = question.get_attribute("id")
        if qid:
            return clean_text(driver.find_element(By.XPATH, f"//*[@aria-labelledby='{qid}']"))
    except:
        pass
 
    #Try to find the answer in the next sibling elements
    try:
        for sib in question.find_elements(By.XPATH, "following-sibling::*[position() <= 3]"):
            txt = clean_text(sib)
            if len(txt) > 10:
                return txt
    except:
        pass
 
    return "Content not found"
 
# -- Recursive scraper --
def crawl(driver, url, depth, visited, rows):
    #Skip URL(s) that have already been visited
    if url in visited:
        return
    visited.add(url)
 
    #Print to see current progress
    print(f"{'  '*depth}→ Scraping (depth {depth}): {url}")
 
    parent = driver.current_window_handle
    if depth > 0:
        #Open subpage in a new tab if depth > 0
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(3)
 
    try:
        #Accept cookies if the popup appears
        try:
            driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
        except:
            pass
 
        #Scroll to load dynamic content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
 
        #Find all possible question elements
        questions = driver.find_elements(By.XPATH, "//h2 | //h3 | //button | //dt")
        seen = set()
 
        for q in questions:
            q_text = clean_text(q)
 
            #Filter out non-questions or duplicates
            if "?" not in q_text or len(q_text) < 10 or q_text in seen:
                continue
            seen.add(q_text)
 
            #Category
            category = "NA"
            try:
                #Retrieve preceding section titles
                all_parents = q.find_elements(By.XPATH, "preceding::*[self::h1 or self::h2]")
               
                if all_parents:
                    closest_parent = all_parents[-1]
                    closest_txt = clean_text(closest_parent).lower()
 
                    #Ignore generic FAQ section titles
                    forbidden_phrases = ["faq", "frequently asked questions", "questions fréquentes"]
               
                    if any(phrase in closest_txt for phrase in forbidden_phrases):
                        category = "NA"
                    else:
                        titles = []
                        #Keep up to the last two section titles
                        for p in all_parents[-2:]:
                            txt = clean_text(p)
                            txt_lower = txt.lower()
                            if txt and not any(phrase in txt_lower for phrase in forbidden_phrases) \
                               and "geforce nom faqs" not in txt_lower:
                                titles.append(txt)
                       
                        unique_titles = list(dict.fromkeys(titles))
                        category = ", ".join(unique_titles[-2:]) if unique_titles else "NA"
                else:
                    category = "NA"
            except:
                category = "NA"
           
            #Answer
            answer = get_answer(driver, q)
 
            #Links extraction
            links_urls = []
            links_names = []
            links_titles = []
 
            try:
                qid = q.get_attribute("id")
                answer_container = None
                if qid:
                    try:
                        answer_container = driver.find_element(By.XPATH, f"//*[@aria-labelledby='{qid}']")
                    except: pass
               
                if not answer_container:
                    potential_links = q.find_elements(By.XPATH, "following-sibling::*[position() <= 2]//a")
                else:
                    potential_links = answer_container.find_elements(By.TAG_NAME, "a")
 
                for a in potential_links:
                    #Ensure the link is valid
                    href = a.get_attribute("href")
                    if href and "http" in href and href != url and href not in links_urls:
                        links_urls.append(href)
                        links_names.append(clean_text(a))
                       
                        #Fetch the title of the linked page
                        t = get_link_title(driver, href)
                        links_titles.append(t)
                   
                    if len(links_urls) >= 5:
                        break
            except:
                pass
 
            #Joins multiple items with a comma
            def format_for_csv(items):
                if not items:
                    return "NA"
                joined_text = ", ".join(items)
                return joined_text
 
            #Save data
            rows.append({
                "site_name": SITE_NAME,
                "url": url,
                "question": q_text,
                "answer": answer,
                "category": category,
                "internal_link": 1 if links_urls else 0,
                "link_name": format_for_csv(links_names),
                "linked_page_title": format_for_csv(links_titles)
            })
 
            #Recursion
            if depth < MAX_DEPTH:
                for l_url in links_urls:
                    crawl(driver, l_url, depth + 1, visited, rows)
 
    finally:
        if depth > 0:
            driver.close()
            driver.switch_to.window(parent)
 
#MAIN
def main():
 
    #Configure Chrome options
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
 
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options)
 
    data = []
    visited = set()
 
    try:
        #Load the main FAQ page
        driver.get(MAIN_URL)
        time.sleep(2)
 
        #Start scraping
        crawl(driver, MAIN_URL, 0, visited, data)
       
        #Save results to CSV
        df = pd.DataFrame(data)
        df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        print(f"\nFile saved at:\n{OUTPUT_FILE}")
 
    finally:
        driver.quit()
 
if __name__ == "__main__":
    main()