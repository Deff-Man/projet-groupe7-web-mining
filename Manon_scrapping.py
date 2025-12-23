import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 1. Importation de tes modules (fichiers .py)
# Assure-toi que les fichiers sont dans le même dossier
from Notion_scrapping import run_notion
from Adobe_scrapping import run_adobe

def main():
    # --- CONFIGURATION ---
    # Chemin vers ton dossier de sortie (Master 1 Web Mining)
    OUTPUT_FOLDER = r"C:\Users\User\Desktop\Master 1\Web mining\Scrapper"
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    FINAL_OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "notion_faq_commun.csv")

    # Configuration du Driver Selenium (Une seule fois pour tout le projet)
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Lancement du navigateur
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Liste pour stocker les DataFrames de chaque site
    all_dataframes = []

    try:
        print("Starting the Global FAQ Scraper...")
        print("="*40)


        # --- MODULE 3: NOTION ---
        print("\n[Step 3/3] Running Notion Module...")
        df_notion = run_notion(driver)
        if not df_notion.empty:
            all_dataframes.append(df_notion)
            print(f"Notion done: {len(df_notion)} rows found.")

        # --- MODULE 3: NOTION ---
        print("\n[Step 3/3] Running Adobe Module...")
        df_adobe = run_adobe(driver)
        if not df_adobe.empty:
            all_dataframes.append(df_adobe)
            print(f"Adobe done: {len(df_adobe)} rows found.")

        # --- FUSION & SAUVEGARDE ---
        if all_dataframes:
            print("\n" + "="*40)
            print("Merging all results...")
            
            # Concaténation des DataFrames (ignore_index réinitialise les numéros de ligne)
            final_df = pd.concat(all_dataframes, ignore_index=True)

            # Sauvegarde en format CSV compatible Excel
            final_df.to_csv(FINAL_OUTPUT_FILE, index=False, encoding="utf-8-sig")
            
            print(f" SUCCESS: Consolidated file saved at:")
            print(f"{FINAL_OUTPUT_FILE}")
            print(f"Total rows collected: {len(final_df)}")
        else:
            print("\nNo data collected from any site.")

    except Exception as e:
        print(f"\nCRITICAL ERROR during orchestration: {e}")

    finally:
        # Fermeture propre du navigateur
        print("\nClosing browser...")
        driver.quit()
        print("Process finished.")

if __name__ == "__main__":
    main()