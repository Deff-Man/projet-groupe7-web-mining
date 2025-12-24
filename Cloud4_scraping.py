from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
import os
import time
import pandas as pd
 
#CONFIGURATION
BASE_URL = "https://cloud.ibm.com/docs/schematics?topic=schematics-general-faq&mhsrc=ibmsearch_a&mhq=faq&locale=en"
SITE_NAME = "IBM Cloud"
 
def format_for_csv(items):
    if not items:
        return "NA"
    return ", ".join(items)
 
def fetch_link_title(context, url):
    """Open a link in a new tab and get its title from div.contentHeader_Title, or NA."""
    title = "NA"
    try:
        page = context.new_page()
        page.goto(url, timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        # Cherche la div qui contient le titre
        div_title = soup.find("div", class_="contentHeader_Title")
        title = div_title.get_text(strip=True) if div_title else "NA"
        page.close()
    except:
        pass
    return title
 
#SCRAPING
def run_ibm(driver):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
 
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
 
        rows = []
        seen_questions = set()
 
        #COLLECT FAQ SECTIONS
        faq_sections = soup.select("section[data-hd-content-type='faq']")
        print("FAQ sections found:", len(faq_sections))
 
        for section in faq_sections:
            h2 = section.find("h2")
            if not h2:
                continue
 
            question = h2.get_text(strip=True)
            if question in seen_questions:
                continue
            seen_questions.add(question)
 
            #Collect answers
            answers = []
            link_names = []
            linked_titles = []
            for p_tag in section.find_all("p"):
                answers.append(p_tag.get_text(" ", strip=True))
                for a in p_tag.find_all("a", href=True):
                    link_names.append(a.get_text(strip=True))
 
                    href = a["href"]
                    if href.startswith("/"):
                        href = "https://cloud.ibm.com" + href
 
                    linked_titles.append(fetch_link_title(context, href))
 
            rows.append({
                "site_name": SITE_NAME,
                "url": BASE_URL,
                "question": question,
                "answer": " ".join(answers),
                "category": "NA",
                "internal_link": 1 if link_names else 0,
                "link_name": ", ".join(link_names) if link_names else "NA",
                "linked_page_title": ", ".join(linked_titles) if linked_titles else "NA"
            })
 
        browser.close()
    return pd.DataFrame(rows)