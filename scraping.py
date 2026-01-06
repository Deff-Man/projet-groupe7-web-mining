import pandas as pd
import os

from Scripts.Scraping.data_collection_merging.Manon_scrapping import run_manon
from Scripts.Scraping.data_collection_merging.Matthieu_scraping import run_matthieu
from Scripts.Scraping.data_collection_merging.put_together import run_zoe


def main_():
    # Define the output and file path
    OUTPUT_FOLDER = r"C:\Users\User\Desktop\Master 1\Web mining\Scrapper"
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    FINAL_OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "faq_commun.csv")

    print("Global scraping launch")
    
    all_dfs = []

    # 1. Collect data from Manon_scrapping.py
    print("\n--- Manon ---")
    try:
        df_manon = run_manon()
        if df_manon is not None and not df_manon.empty:
            all_dfs.append(df_manon)
            print(f"-> Manon: {len(df_manon)} rows successfully retrieved.")
        else:
            print("-> Manon: No data found.")
    except Exception as e:
        print(f"-> Critical error in Manon's sector: {e}")

    # 2. Collect data from Matthieu_scraping.py
    print("\n--- Matthieu ---")
    try:
        df_matthieu = run_matthieu()
        if df_matthieu is not None and not df_matthieu.empty:
            all_dfs.append(df_matthieu)
            print(f"-> Matthieu: {len(df_matthieu)} rows successfully retrieved.")
        else:
            print("-> Matthieu: No data found.")
    except Exception as e:
        print(f"-> Critical error in Matthieu's sector: {e}")

   # 3. Collect data from Zoe_scraping.py (put_together.py)
    print("\n--- Zoe ---")
    try:
        df_zoe = run_zoe()
        if df_zoe is not None and not df_zoe.empty:
            all_dfs.append(df_zoe)
            print(f"-> Zoe: {len(df_zoe)} rows successfully retrieved.")
        else:
            print("-> Zoe: No data found.")
    except Exception as e:
        print(f"-> Critical error in Zoe's sector: {e}")


    # 3. Save data
    if all_dfs:
        final_all = pd.concat(all_dfs, ignore_index=True)
        final_all.to_csv(FINAL_OUTPUT_FILE, index=False, encoding="utf-8-sig")
        
        print(f"Success")
        print(f"Consolidated file saved at: {FINAL_OUTPUT_FILE}")
        print(f"Total rows collected : {len(final_all)}")
    else:
        print("\n No data was collected. No file was created.")

if __name__ == "__main__":
    main_()