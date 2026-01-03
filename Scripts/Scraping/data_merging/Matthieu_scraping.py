import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import inspect
 
# Import scrapping modules
from Cisco_scraping import run_cisco
from Cloud_scraping import run_ibm_cloud
from Ibmtaxi_scraping import run_ibmtaxi
from Ibm3_scraping import run_ibm3
from Cloud4_scraping import run_ibm
from Docusign_scraping import run_docusign
from Intel_scraping import run_intel
from Docker_scraping import run_docker
from Nvidia_scraping import run_nvidia
 
def run_matthieu():
 
    # Configure Chrome options
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
   
    # Initialize the WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
 
    # List to store results from each site
    all_dataframes = []
 
    # Map of scrapers to execute
    scrapers = [
        ("Cisco", run_cisco),
        ("Cloud", run_ibm_cloud),
        ("Ibmtaxi", run_ibmtaxi),
        ("Ibm3", run_ibm3),
        ("Cloud4", run_ibm),
        ("Docusign", run_docusign),
        ("Intel", run_intel),
        ("Docker", run_docker),
        ("Nvidia", run_nvidia)]
 
    try:
 
        # Loop through each scraper to collect data
        for name, func in scrapers:
            print(f"\n[Running] {name} Scrapping : ")
            try:
                # Execute the scrapping function
                if len(inspect.signature(func).parameters) == 1:
                    df = func(driver)   # Selenium scrapers
                else:
                    df = func()         # Playwright / Requests scrapers
 
               
                # Check if data was successfully collected
                if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                    all_dataframes.append(df)
                    print(f"-> {name} success: {len(df)} rows found.")
                else:
                    print(f"-> {name} warning: No data returned.")
 
            except Exception as e:
                # Individual module error
                print(f"-> {name} failed: {e}")
 
        # Data saving
        if all_dataframes:
            return pd.concat(all_dataframes, ignore_index=True)
        return pd.DataFrame()
 
    finally:
        driver.quit()