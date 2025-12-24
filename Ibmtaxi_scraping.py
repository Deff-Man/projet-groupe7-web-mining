import requests
from bs4 import BeautifulSoup
import csv
from urllib.parse import urljoin
import os
import pandas as pd

#Configuration
BASE_URL = "https://oasis-open.github.io"
FAQ_URL = f"{BASE_URL}/cti-documentation/faq"
SITE_NAME = "IBM"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def run_ibmtaxi():
    
    #Request FAQ page
    response = requests.get(FAQ_URL, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    elements = soup.find_all(["h2", "h3", "p"])

    #Storage
    data = []
    current_category = None
    current_question = None
    current_answer = []
    link_names = []
    linked_page_titles = []

    #Helpers
    def is_internal_link(href):
        return href and href.startswith("/cti-documentation")

    def fetch_page_title(href):
        try:
            full_url = urljoin(BASE_URL, href)
            r = requests.get(full_url, headers=HEADERS, timeout=5)
            r.raise_for_status()
            page_soup = BeautifulSoup(r.text, "html.parser")
            h1 = page_soup.find("h1")
            return h1.get_text(strip=True) if h1 else "NA"
        except:
            return "NA"

    def save_current():
        if current_category and current_question and current_answer:
            data.append({
                "site_name": SITE_NAME,
                "url": FAQ_URL,
                "question": current_question,
                "answer": " ".join(current_answer).strip(),
                "category": current_category,
                "internal_link": 1 if link_names else 0,
                "link_name": ", ".join(link_names) if link_names else "NA",
                "linked_page_title": ", ".join(linked_page_titles) if linked_page_titles else "NA"
            })


    #Parse elements
    for el in elements:

        #Category
        if el.name == "h2":
            save_current()
            current_category = el.get_text(" ", strip=True)
            current_question = None
            current_answer = []
            link_names = []
            linked_page_titles = []

        #Question
        elif el.name == "h3":
            save_current()
            current_question = el.get_text(" ", strip=True)
            current_answer = []
            link_names = []
            linked_page_titles = []

        #Answer
        elif el.name == "p" and current_question:
            text = el.get_text(" ", strip=True)
            if text:
                current_answer.append(text)

            for a in el.find_all("a", href=True):
                if is_internal_link(a["href"]):
                    name = a.get_text(strip=True)
                    if name not in link_names:
                        link_names.append(name)
                        linked_page_titles.append(fetch_page_title(a["href"]))
                        
    #Save last FAQ
    save_current()
    return pd.DataFrame(data)