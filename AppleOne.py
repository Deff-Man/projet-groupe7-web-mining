import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import os
import re

# Main URL to start scraping
URL = "https://www.apple.com/apple-one/"
SITE_NAME = "Apple One"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

#Standardizes text by removing newlines, tabs, and collapsing multiple spaces.
def clean_text(text):
    
    if not text: return "NA"

    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

#Fetches the title of a linked page. Attempts to find Apple-specific H2 headers first, falling back to the <title> tag.
def get_apple_custom_title(url):
    try:
        if not url or url == "NA" or "#" in url: return "Internal page"
        res = requests.get(url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            s = BeautifulSoup(res.text, "html.parser")
            
            h2_title = s.find("h2", class_="sc-one-home")
            if h2_title:
                return clean_text(h2_title.get_text())
            return clean_text(s.title.get_text()) if s.title else "Untitled"
    except:
        pass
    return "Error"

def run_apple_one() :
    # Send HTTP request to the main page
    # .raise_for_status() ensures the script stops if the page fails to load
    response = requests.get(URL, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Locate the FAQ section by its ID or class name
    faq_section = soup.find("section", id="faq") or soup.find("section", class_="section-faq")
    rows = []

    if faq_section:
        # Iterate through each list item which represents a Question/Answer pair
        for li in faq_section.find_all("li"):
            q_tag = li.find(["button", "h3", "strong"])
            if not q_tag: continue
            
            question = clean_text(q_tag.get_text())
            # Locate the answer
            answer_tag = li.find("div", class_="answer") or li.find("p", class_="typography-faq-answer")
            answer = clean_text(answer_tag.get_text()) if answer_tag else "NA"

            #Extract and categorize links found within the answer
            links = li.find_all("a", href=True)
            internal_link_binary = 0
            link_names = []
            linked_page_titles = []

            if links:
                for link in links:
                    href = link["href"]
                    name = clean_text(link.get_text())
                    link_names.append(name)
                    
                    if href.startswith("/") or "apple.com" in href:
                        internal_link_binary = 1
                        if href.startswith("#"):
                            linked_page_titles.append("Internal anchor")
                        else:
                            # Join relative paths with base URL and crawl the linked page title
                            full_url = urljoin(URL, href)
                            linked_page_titles.append(get_apple_custom_title(full_url))
                    else:
                        linked_page_titles.append("External link")

            rows.append({
                "site_name": SITE_NAME,
                "url": URL,
                "question": question,
                "answer": answer,
                "category": "NA",
                "internal_link": internal_link_binary,
                "link_name": ", ".join(link_names) if link_names else "NA",
                "linked_page_title": ", ".join(linked_page_titles) if linked_page_titles else "NA"
            })
    return pd.DataFrame(rows)
    
