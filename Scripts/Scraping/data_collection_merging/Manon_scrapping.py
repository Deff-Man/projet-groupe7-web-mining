import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# Import scrapping modules
from Notion_scrapping import run_notion
from Adobe_scrapping import run_adobe
from Dropbox_scraping import run_dropbox
from SAP_scrapping import run_sap
from Salesforce_scrapping import run_salesforce
from zoom_scraping import run_zoom

def run_manon():
    # Configure Chrome options 
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")

    # Initialize the WebDriver 
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # List to store results from each site
    all_dataframes = []

    # Map of scrapers to execute
    scrapers = [
        ("Notion", run_notion),
        ("Adobe", run_adobe),
        ("Dropbox", run_dropbox),
        ("SAP", run_sap),
        ("Salesforce", run_salesforce),
        ("Zoom", run_zoom)]

    try:

        # Loop through each scraper to collect data
        for name, func in scrapers:
            print(f"\n[Running] {name} Scrapping : ")
            try:
                # Execute the scrapping function
                df = func(driver)
                
                # Check if data was successfully collected
                if df is not None and not df.empty:
                    all_dataframes.append(df)
                    print(f"-> {name} success: {len(df)} rows found.")
                else:
                    print(f"-> {name} warning: No data returned.")

            except Exception as e:
                # Individual module error 
                print(f"-> {name} failed: {e}")

        if all_dataframes:
            return pd.concat(all_dataframes, ignore_index=True)
        return pd.DataFrame() 

    finally:
        driver.quit()

