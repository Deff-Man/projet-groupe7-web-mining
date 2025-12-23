import time
import os
import pandas as pd
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
 
#Main URL to start scraping
MAIN_URL = "https://www.intel.com/content/www/us/en/developer/get-help/faq.html"
SITE_NAME = "Intel"
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
        #Prefer H1, fallback to document.title, then meta tags
        try:
            h1 = driver.find_element(By.TAG_NAME, "h1")
            title = clean_text(h1)
        except:
            #fallback to JS/document title
            try:
                title_text = driver.title
                if title_text and title_text.strip():
                    title = " ".join(title_text.split())
                else:
                    #try common meta tags (og:title or meta[name=title])
                    try:
                        meta = driver.find_element(By.XPATH, "//meta[@property='og:title' or @name='title']")
                        meta_content = meta.get_attribute('content')
                        if meta_content:
                            title = " ".join(meta_content.split())
                    except:
                        pass
            except:
                pass
        driver.close()
    except:
        pass
    finally:
        try:
            driver.switch_to.window(parent)
        except:
            #If switching back fails, ignore to avoid crashing the crawl
            pass
 
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
        #First try: nearby following siblings (existing logic)
        for sib in question.find_elements(By.XPATH, "following-sibling::*[position() <= 3]"):
            txt = clean_text(sib)
            if len(txt) > 10:
                return txt

        #Fallbacks: some sites place the answer deeper or in following div/section/p
        for elem in question.find_elements(By.XPATH, "(following::div | following::section | following::p)[position() <= 6]"):
            txt = clean_text(elem)
            if len(txt) > 20:
                return txt
    except:
        pass
 
    return "Content not found"
 
#Recursive scraper
def crawl(driver, url, depth, visited, seen_questions, rows):
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
            if "?" not in q_text or len(q_text) < 10 or q_text in seen_questions:
                continue
            seen_questions.add(q_text)
 
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
                               and "product licensing" not in txt_lower:
                                titles.append(txt)
                       
                        unique_titles = list(dict.fromkeys(titles))
                        category = ", ".join(unique_titles[-2:]) if unique_titles else "NA"
                else:
                    #Fallback: inspect ancestor elements to find a nearby heading
                    try:
                        forbidden_phrases = ["faq", "frequently asked questions", "questions fréquentes"]
                        ancestors = q.find_elements(By.XPATH, "ancestor::*")
                        chosen = None
                        #look up to 6 nearest ancestors
                        for anc in ancestors[-6:][::-1]:
                            try:
                                heading = anc.find_element(By.XPATH, ".//h2 | .//h1 | .//h3")
                                htxt = clean_text(heading)
                                hlow = htxt.lower()
                                if htxt and not any(phrase in hlow for phrase in forbidden_phrases) and "intel" not in hlow:
                                    chosen = htxt
                                    break
                            except:
                                continue

                        category = chosen if chosen else "NA"
                    except:
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
                    #Prefer explicit FAQ answer containers often used on the site
                    try:
                        #Strategy A: following sibling div with class 'faq-answers'
                        sib = q.find_elements(By.XPATH, "following-sibling::div[contains(@class, 'faq-answers')][position() <= 3]")
                        if sib:
                            answer_container = sib[0]
                        else:
                            #Strategy B: if the question contains a button with href like '#id', use that id
                            try:
                                btn = q.find_element(By.XPATH, ".//button[@href or @data-bs-target]")
                                href = btn.get_attribute('href') or btn.get_attribute('data-bs-target')
                                if href and href.startswith('#'):
                                    aid = href.lstrip('#')
                                    try:
                                        answer_container = driver.find_element(By.ID, aid)
                                    except:
                                        answer_container = None
                            except:
                                answer_container = None
                    except:
                        answer_container = None

                #Only extract links if we found an explicit answer container
                if answer_container:
                    potential_links = answer_container.find_elements(By.TAG_NAME, "a")
                else:
                    potential_links = []
 
                for a in potential_links:
                    #Get link text and href
                    href = a.get_attribute("href")
                    link_text = clean_text(a)
                    
                    #Skip empty links or duplicates
                    if not link_text or not href:
                        continue
                    
                    #Convert relative URLs to absolute URLs if needed
                    if href.startswith("/"):
                        base_url = "https://www.intel.com"
                        try:
                            base_url = url.split("/content/")[0] if "/content/" in url else "https://www.intel.com"
                        except:
                            pass
                        href = urljoin(base_url, href)
                    
                    #Skip non-http links, duplicates, and self-links
                    if href and "http" in href and href != url and href not in links_urls:
                        links_urls.append(href)
                        links_names.append(link_text)

                        #Fetch the title of the linked page
                        t = get_link_title(driver, href)
                        links_titles.append(t)
                   
                    if len(links_urls) >= 5:
                        break
            except Exception as e:
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
                    crawl(driver, l_url, depth + 1, visited, seen_questions, rows)
 
    finally:
        if depth > 0:
            driver.close()
            driver.switch_to.window(parent)
 
#MAIN
def run_intel(driver):
 
    data = []
    visited = set()
    seen_questions = set()
 
    #Load the main FAQ page
    driver.get(MAIN_URL)
    time.sleep(2)
 
    #Start scraping
    crawl(driver, MAIN_URL, 0, visited, seen_questions, data)
       
    print(f" Finished Intel FAQ scraping ({len(data)}) rows")
    return pd.DataFrame(data)
