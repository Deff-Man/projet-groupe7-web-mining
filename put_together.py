import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Import scrapping modules
from AirBNB import run_airbnb
from AppleArcade import run_apple_arcade
from AppleMusic import run_apple_music
from AppleOne import run_apple_one
from AppleTV import run_apple_tv
from Asana import scrape_asana
from Github import scrape_github
from Pinterest import scrape_pinterest_final
from ProtonMail import run_ProtonMail
from Telegram import scrape_telegram_faq

def run_zoe():

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
        ("Asana",scrape_asana),
        ("AirBNB", run_airbnb),
        ("AppleArcade", run_apple_arcade),
        ("AppleMusic", run_apple_music),
        ("AppleOne", run_apple_one),
        ("AppleTV", run_apple_tv),
        ("Github", scrape_github),
        ("Pinterest", scrape_pinterest_final),
        ("ProntonMail", run_ProtonMail),
        ("Telegram", scrape_telegram_faq)]
    try:
        # Loop through each scraper to collect data
        for name, func in scrapers:
            print(f"\n[Running] {name} Scrapping : ")
            try:
                # Execute the scrapping function
                if name == "Github" or name == "AppleOne" or name == "Asana" or name == "Pinterest" or name == "Telegram" :
                    df = func()
                else:
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

        # Data saving
        if all_dataframes:
            return pd.concat(all_dataframes, ignore_index=True)
        return pd.DataFrame()

    finally:
        driver.quit()