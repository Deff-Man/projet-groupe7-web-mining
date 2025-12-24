from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests
import pandas as pd

# CONFIGURATION
BASE_URL = "https://exchange.xforce.ibmcloud.com/faq?mhsrc=ibmsearch_a&mhq=faq&_gl=1*y45q7e*_ga*MjM3OTU1NTI0LjE3NjU3MzM4ODg.*_ga_FYECCCS21D*czE3NjYyNTAzNDYkbzYkZzEkdDE3NjYyNTA1NzkkajIwJGwwJGgw"
SITE_NAME = "IBM"

# --- Helper pour récupérer le titre d'un lien ---
def fetch_link_title_requests(url):
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in ["h1", "h2", "span"]:
            elem = soup.find(tag)
            if elem:
                return elem.get_text(strip=True)
    except:
        return "NA"
    return "NA"

# --- Scraping principal ---
def run_ibm3():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL)
        page.wait_for_selector("h4.faqquestion")

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        rows = []

        # Parse sections
        sections = soup.find_all("h3", class_="sectionheading")
        for section in sections:
            category = section.get_text(strip=True) if section else "NA"

            # Questions et réponses dans la section
            for q in section.find_all_next("h4", class_="faqquestion"):
                next_section = q.find_previous("h3", class_="sectionheading")
                if next_section != section:
                    break

                question = q.get_text(strip=True)
                answer_elem = q.find_next("p", class_="faqanswer")
                answer = answer_elem.get_text(" ", strip=True) if answer_elem else "Content not found"

                # Liens dans la réponse
                link_names = []
                linked_titles = []
                if answer_elem:
                    for a in answer_elem.find_all("a", href=True):
                        link_names.append(a.get_text(strip=True))
                        linked_titles.append(fetch_link_title_requests(a["href"]))

                rows.append({
                    "site_name": SITE_NAME,
                    "url": BASE_URL,
                    "category": category,
                    "question": question,
                    "answer": answer,
                    "internal_link": 1 if link_names else 0,
                    "link_name": ", ".join(link_names) if link_names else "NA",
                    "linked_page_title": ", ".join(linked_titles) if linked_titles else "NA"
                })

        browser.close()
    return pd.DataFrame(rows)