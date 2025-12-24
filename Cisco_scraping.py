import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from urllib.parse import urljoin
from webdriver_manager.chrome import ChromeDriverManager

#Main URL to start scraping
MAIN_URL = "https://web-help.cisco.com/faq"
SITE_NAME = "CISCO"
MAX_DEPTH = 1  #Main page + linked pages

#Helper functions

def clean_text(element):
    """Remove extra spaces from element text."""
    return " ".join(element.get_attribute("textContent").split())

def get_link_title(driver, url):
    """Get the H1 title of a linked page using a temporary tab."""
    parent = driver.current_window_handle
    title = "NA"  #Default NA
    try:
        #ignore invalid or javascript links
        if not url or url.strip() == "" or url.lower().startswith("javascript"):
            return title

        #open a new tab and navigate explicitly to avoid about:blank
        driver.switch_to.new_window('tab')
        driver.get(url)
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
            title_text = clean_text(driver.find_element(By.TAG_NAME, "h1"))
            if title_text:
                title = title_text
        except TimeoutException:
            title = driver.title if driver.title else "NA"
        driver.close()
    except:
        pass
    finally:
        try:
            driver.switch_to.window(parent)
        except:
            pass
    return title

def get_answer(driver, q):
    """Click on the accordion to reveal the answer and extract it."""
    try:
        driver.execute_script("arguments[0].click();", q)
        time.sleep(0.5)  #wait for accordion to open
    except:
        pass

    try:
        #Answer is in the next sibling with class muse-accordion-body
        answer_div = q.find_element(By.XPATH, "following-sibling::div[contains(@class,'muse-accordion-body')]")
        return answer_div.text.strip()
    except:
        return "Content not found"

#Recursive scraper

def crawl(driver, url, depth, visited, seen_questions, rows):
    if url in visited:
        return
    visited.add(url)

    print(f"{'  '*depth}→ Scraping (depth {depth}): {url}")

    parent = driver.current_window_handle
    if depth > 0:
        try:
            driver.switch_to.new_window('tab')
            driver.get(url)
        except Exception:
            try:
                driver.execute_script(f"window.open('{url}', '_blank');")
                driver.switch_to.window(driver.window_handles[-1])
            except Exception:
                pass
        time.sleep(2)

    try:
        #Accept cookies if popup appears
        try:
            driver.find_element(By.XPATH, "//button[contains(., 'Accept')]").click()
            time.sleep(1)
        except:
            pass

        #Scroll to load dynamic content
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception:
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                for _ in range(3):
                    body.send_keys(Keys.PAGE_DOWN)
                    time.sleep(0.5)
            except Exception:
                pass
        time.sleep(1)

        #Extract "Most Popular Questions" if present on the page
        try:
            headings = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'most popular')]")
            for h in headings:
                container = None
                try:
                    container = h.find_element(By.XPATH, "following-sibling::*[1]")
                except:
                    pass
                if container:
                    for a in container.find_elements(By.TAG_NAME, "a"):
                        q_text = a.text.strip()
                        href = a.get_attribute("href")
                        if not q_text or not href:
                            continue
                        if href.startswith('javascript') or href.strip() in ('', '#'):
                            print(f"  ! Ignored Most Popular link (invalid): {href}")
                            continue
                        href = urljoin(url, href)
                        rows.append({
                            "site_name": SITE_NAME,
                            "url": url,
                            "question": q_text,
                            "answer": "NA",
                            "category": "Most Popular",
                            "internal_link": 1,
                            "link_name": q_text,
                            "linked_page_title": "NA"  #NA by default
                        })
        except Exception:
            pass

        #Find all question elements in accordions
        try:
            questions = WebDriverWait(driver, 3).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".muse-accordion-title"))
            )
        except TimeoutException as e:
            print(f"  ! Warning: no question elements found (wait timed out): {e}")
            questions = []
        except Exception as e:
            print(f"  ! Warning: skipping page due to selector/JS error: {e}")
            questions = []
        seen = set()
        print("Questions found:", len(questions))

        for q in questions:
            q_text = clean_text(q)
            if len(q_text) < 5 or q_text in seen_questions:
                continue
            seen_questions.add(q_text)

            category = "NA"
            answer = get_answer(driver, q)

            #Links extraction
            links_urls = []
            links_names = []
            links_titles = []

            try:
                qid = q.get_attribute("aria-controls")
                answer_container = None
                if qid:
                    try:
                        answer_container = driver.find_element(By.ID, qid)
                    except: pass

                if not answer_container:
                    potential_links = q.find_elements(By.XPATH, "following-sibling::*[position() <= 2]//a")
                else:
                    potential_links = answer_container.find_elements(By.TAG_NAME, "a")

                for a in potential_links:
                    href = a.get_attribute("href")
                    name = clean_text(a)
                    if not href or href.strip() == '' or href.strip() == '#' or href.startswith('javascript'):
                        print(f"    ! Ignored link (bad href): {href}")
                        continue
                    href = urljoin(url, href)
                    if href not in links_urls:
                        links_urls.append(href)
                        links_names.append(name if name else href)
                        try:
                            t = get_link_title(driver, href)
                            if not t:  #Empty → NA
                                t = "NA"
                        except Exception:
                            t = "NA"
                        links_titles.append(t)
                    if len(links_urls) >= 5:
                        break
            except:
                pass

            rows.append({
                "site_name": SITE_NAME,
                "url": url,
                "question": q_text,
                "answer": answer,
                "category": category,
                "internal_link": 1 if links_urls else 0,
                "link_name": ", ".join(links_names) if links_names else "NA",
                "linked_page_title": ", ".join(links_titles) if links_titles else "NA"
            })

            if depth < MAX_DEPTH:
                for l_url in links_urls:
                    crawl(driver, l_url, depth + 1, visited, seen_questions, rows)

    finally:
        if depth > 0:
            driver.close()
            driver.switch_to.window(parent)

#MAIN

def run_cisco(driver):
    
    data = []
    visited = set()
    seen_questions = set()

    #load main page
    driver.get(MAIN_URL)
    time.sleep(2)
    crawl(driver, MAIN_URL, 0, visited, seen_questions, data)

    print(f" Finished Cisco FAQ scraping ({len(data)} rows).")
    return pd.DataFrame(data)