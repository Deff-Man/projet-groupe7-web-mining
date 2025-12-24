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
 
def main():
    # Define the output and file path
    OUTPUT_FOLDER = "/Users/matthieubeaumont/Desktop/Bureau/Projet_FAQ_web_mining/faq_scraper/faq_scraper/spiders"
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    FINAL_OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "faq_commun.csv")
 
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
 
            # Concatenate all collected DataFrames
            final_df = pd.concat(all_dataframes, ignore_index=True)
 
            # Export to CSV
            final_df.to_csv(FINAL_OUTPUT_FILE, index=False, encoding="utf-8-sig")
           
            print(f"SUCCESS: Consolidated file saved at :")
            print(f"{FINAL_OUTPUT_FILE}")
            print(f"Total rows collected across all sites: {len(final_df)}")
        else:
            print("\nProcess finished but no data was collected from any site.")
 
    except Exception as e:
        print(f"\nCRITICAL ERROR during orchestration: {e}")
 
    finally:
        driver.quit()
 
if __name__ == "__main__":
    main()