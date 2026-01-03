import pandas as pd
import csv
import io
from pathlib import Path
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory

# set seed for consistent language detection
DetectorFactory.seed = 0

# input and output file paths
in_path = Path(r"C:\Users\User\Desktop\Master 1\Web mining\faq_commun.csv")
out_path = Path(r"C:\Users\User\Desktop\Master 1\Web mining\faq_clean.csv")

# keywords to identify generic link text or URLs
generic_terms = {"here", "docs", "doc", "documentation", "examples", "example", 
    "learn more", "*", "tap", "click here", "click", "read more", "link", "page"}

# strings considered as missing values
na_strings = {"na", "n/a", "nan", "", "none", "null"}

# helper functions

# 1/ normalizes a string value returns 'NA' if the value is empty/null, otherwise returns the stripped string
def clean_str(x):
    if pd.isna(x): 
        return "NA"
    s = str(x).strip()
    return "NA" if s.lower() in na_strings else s

# 2/ checks if text is a URL or a generic word like "click here"
def is_generic_or_url(text):
    s = text.lower()
    return s.startswith(("http", "www.")) or s in generic_terms

# 3/ translates text to English if detected as another language
def translate_text(text):
    text = clean_str(text)
    if text == "NA" or len(text) < 3:
        return text
    try:
        # translate only if not English
        if detect(text) != 'en':
            return GoogleTranslator(source='auto', target='en').translate(text)
    except Exception:
         # keep original text on failure
        pass
    return text

# 4/ selects the most descriptive text between 'link_name' and 'linked_page_title'
def pick_best_link_text(a, b):
    a, b = clean_str(a), clean_str(b)
    
    # handle NA
    if a == "NA": return b
    if b == "NA": return a
    
    # handle generic terms/URLs, we prefer descriptive text
    if is_generic_or_url(a): return b
    if is_generic_or_url(b): return a
    
    # handle substrings, we prefer the longer/more complete version
    if a.lower() in b.lower(): return b
    if b.lower() in a.lower(): return a
    
    # default: return the longer one
    return b if len(b) >= len(a) else a

# 5/ merges 'link_name' and 'linked_page_title' into a single cleaned string
def consolidate_links(row):
    # split by comma and clean
    names = [s.strip() for s in str(row.get("link_name", "")).split(",") if s.strip()]
    titles = [s.strip() for s in str(row.get("linked_page_title", "")).split(",") if s.strip()] 
    
    # pad lists to same length with "NA"
    max_len = max(len(names), len(titles))
    names += ["NA"] * (max_len - len(names))
    titles += ["NA"] * (max_len - len(titles))
    
    # merge pair by pair
    merged_items = []
    seen = set()
    
    for n, t in zip(names, titles):
        best = pick_best_link_text(n, t)
        if best != "NA" and best.lower() not in seen:
            seen.add(best.lower())
            merged_items.append(best)
            
    return ", ".join(merged_items) if merged_items else "NA"

# 6/ standardizes site names (IBM, Apple)
def normalize_site_name(site):
    s = str(site).strip()
    if "IBM" in s: return "IBM"
    if s in {"Apple Arcade", "Apple One", "Tv"}: return "Apple"
    return s

# main
print(" Starting data cleaning :")

# 1/ read data
# read file as string first to handle encoding errors and detect delimiter
raw_content = in_path.read_text(encoding="utf-8", errors="replace")
dialect = csv.Sniffer().sniff("\n".join(raw_content.splitlines()[:50]))
df = pd.read_csv(io.StringIO(raw_content), sep=dialect.delimiter, engine="python")

# handle column name typo from source if exists
if "linked_page_tilte" in df.columns:
    df.rename(columns={"linked_page_tilte": "linked_page_title"}, inplace=True)

# 2/ filter rows
# remove rows with empty answers or questions
df = df.dropna(subset=["answer", "question"])
# filter out "content not found" or empty strings
df = df[~df["answer"].astype(str).str.strip().str.lower().isin(["", "content not found"])]
df = df[~df["question"].astype(str).str.strip().str.upper().isin(["", "NA"])]

# 3/ deduplicate question by site_name
df = df.drop_duplicates(subset=["site_name", "question"], keep="first")

# 4/ translation
df["question"] = df["question"].apply(translate_text)
df["answer"] = df["answer"].apply(translate_text)

# 5/ merge link columns
df["link"] = df.apply(consolidate_links, axis=1)

# 6/ normalize columns
df["site_name"] = df["site_name"].apply(normalize_site_name)
if "category" in df.columns:
    df["category"] = df["category"].apply(clean_str)

# 7/ final cleaning

# remove temporary columns
df = df.drop(columns=["link_name", "linked_page_title"], errors="ignore")

# fix corrupted characters 
df = df.replace("â€™", "'", regex=True)

# convert all fancy quotes to standard apostrophes
df = df.replace(r"[’‘`´]", "'", regex=True)

# fix misplaced '?' inside words
df = df.replace(r"(?<=[a-zA-Z])\?(?=[a-zA-Z])", "'", regex=True)

# remove line breaks to keep data on a single line
df = df.replace(r'\r+|\n+|\t+', ' ', regex=True)

# data export
df.to_csv(out_path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)

print(f"Saved to: {out_path}")
print(f"Final Row Count: {len(df)}")