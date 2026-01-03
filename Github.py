import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from urllib.parse import urljoin, urlparse

url = "https://github.com/frequently-asked-questions" 
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

#Removes extra whitespaces and joins split text into a single line.
def clean_text(text):
    if not text: return "NA"
    return " ".join(text.split())

#Sends a separate GET request to a linked URL to retrieve its HTML <title>. Includes a 3-second timeout to prevent the script from freezing on slow links.
def get_remote_page_title(link_url):
    
    try:
        r = requests.get(link_url, headers=headers, timeout=3)
        if r.status_code == 200:
            s = BeautifulSoup(r.text, 'html.parser')
            if s.title and s.title.string:
                return clean_text(s.title.string)
        return "No Title Found"
    except Exception:
        return "Link Error"

def scrape_github():
    print(f"Connecting to {url}...")
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"HTTP Error: {response.status_code}")
            return pd.DataFrame()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
    except Exception as e:
        print(f"Connection Error: {e}")
        return pd.DataFrame()

    all_data = []
    
    #Target the Site Name
    domain = urlparse(url).netloc
    site_name = domain.replace("www.", "").split(".")[0].capitalize() # e.g. "Github"

    # Find FAQ items
    # Adjust this selector if the FAQ is not in <details> tags
    faq_items = soup.find_all('details')
    print(f"{len(faq_items)} FAQ items found.")

    for index, item in enumerate(faq_items):
        try:
            #Question
            summary = item.find('summary')
            if not summary: continue
            
            # Check for h3/h4 inside summary, otherwise take summary text
            question_tag = summary.find(['h4', 'h3', 'strong'])
            if question_tag:
                question_text = clean_text(question_tag.get_text())
            else:
                question_text = clean_text(summary.get_text())

            print(f"Processing ({index+1}): {question_text[:30]}...")

            # Answer
            # Get full text and subtract the question text
            full_text = item.get_text(" ", strip=True)
            answer_text = full_text.replace(question_text, "", 1).strip()
            answer_text = clean_text(answer_text)

            # Links information
            link_names_list = [] # What is written on the link (link_name)
            link_titles_list = [] # Title of the page it goes to (linked_page_title)
            
            # Find all links NOT inside the summary (Question)
            all_links = item.find_all('a')
            
            for l in all_links:
                # Ensure link is part of the answer, not the question
                if l.parent != summary and l.parent.parent != summary:
                    href = l.get('href')
                    text = clean_text(l.get_text())
                    
                    if href:
                        # Convert relative paths to absolute URLs
                        full_link = urljoin(url, href)
                        
                        if full_link.startswith("http"):
                            link_names_list.append(text if text else "Image/Icon Link")
                            
                            #Visit the linked page to get its meta-title
                            page_title = get_remote_page_title(full_link)
                            link_titles_list.append(page_title)

            # Data storage
            all_data.append({
                "site_name": site_name,
                "url": url,
                "question": question_text,
                "answer": answer_text,
                "category": "NA", #No catogory
                "internal_link": 1 if link_names_list else 0,
                "link_name": ", ".join(link_names_list) if link_names_list else "NA",
                "linked_page_title": ", ".join(link_titles_list) if link_titles_list else "NA"
            })
            
        except Exception as e:
            print(f"Error on item: {e}")
            continue

    return pd.DataFrame(all_data)
