from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
import os
import pandas as pd

Base_URL = "https://cloud.ibm.com/docs/storage-scale?topic=storage-scale-storage-scale-faqs"
SITE_NAME = "IBM Cloud"

def run_ibm_cloud():
    #LOAD PAGE WITH PLAYWRIGHT
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        page.goto(Base_URL)
        page.wait_for_load_state("networkidle")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    #COLLECT FAQ BLOCKS
    faq_sections = soup.select("section[data-hd-content-type='faq']")

    rows = []
    seen_questions = set()

    #PARSE STANDARD FAQ SECTIONS
    for section in faq_sections:
        h2 = section.find("h2")
        if not h2:
            continue

        question = h2.get_text(strip=True)
        if question in seen_questions:
            continue
        seen_questions.add(question)

        answers = []
        link_names = []
        linked_titles = []

        for p_tag in section.find_all("p"):
            answers.append(p_tag.get_text(" ", strip=True))
            for a in p_tag.find_all("a", href=True):
                link_names.append(a.get_text(strip=True))
                linked_titles.append(a.get_text(strip=True))

        rows.append({
            "site_name": SITE_NAME,
            "url": Base_URL,
            "question": question,
            "answer": " ".join(answers),
            "category": "NA",
            "internal_link": 1 if link_names else 0,
            "link_name": ", ".join(link_names) if link_names else "NA",
            "linked_page_title": ", ".join(linked_titles) if linked_titles else "NA"})


    #FALLBACK: LAST FAQS OUTSIDE SECTIONS
    all_h2 = soup.find_all("h2")

    for h2 in all_h2:
        question = h2.get_text(strip=True)

        if question in seen_questions:
            continue

        #Heuristic: only keep real questions
        if "?" not in question:
            continue

        answers = []
        link_names = []
        linked_titles = []

        for sib in h2.find_next_siblings():
            if sib.name == "h2":
                break
            if sib.name == "p":
                answers.append(sib.get_text(" ", strip=True))
                for a in sib.find_all("a", href=True):
                    link_names.append(a.get_text(strip=True))
                    linked_titles.append(a.get_text(strip=True))

        if answers:
            seen_questions.add(question)
            rows.append({
                "site_name": SITE_NAME,
                "url": Base_URL,
                "question": question,
                "answer": " ".join(answers),
                "category": "NA",
                "internal_link": 1 if link_names else 0,
                "link_name": ", ".join(link_names) if link_names else "NA",
                "linked_page_title": ", ".join(linked_titles) if linked_titles else "NA"})
    return pd.DataFrame(rows)