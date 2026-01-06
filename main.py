# Pipeline - Faq Analysis - Project
# This script orchestrates the full workflow : 
# 1/ Scraping & Cleaning
# 2/ Text Mining (Core, Descriptive, Semantic)
# 3/ Link Analysis

import pandas as pd
import os
import subprocess
import sys

# injects the scraping directory into sys.path to allow internal 
base_path = os.path.dirname(os.path.abspath(__file__))
scraping_path = os.path.join(base_path, "Scripts", "Scraping", "data_collection_merging")
if scraping_path not in sys.path:
    sys.path.append(scraping_path)

# importing main execution functions
from Scripts.Scraping.data_collection_merging.scraping import main_ as launch_scraping
from Scripts.Text_mining.text_mining import main as launch_text_mining
from Scripts.Link_analysis.link_analysis_ import main as launch_link_analysis

# configuration
run_scraper = False  

# data path : update these paths to match your machine's directory structure.
# data_raw is the output of the scraping process.
data_raw = r"C:\Users\User\Desktop\Master 1\Web mining\faq_commun.csv"
# data_clean is the output of the cleaning script and input for text mining analysis.
data_clean = r"C:\Users\User\Desktop\Master 1\Web mining\faq_clean.csv"

# path scripts
cleaning_script = r"Scripts/Scraping/data_cleaning/cleaning_data.py"
semantic_script = r"Scripts/Text_mining/semantic_textmining_application.py" 
matrix_adjacency_script = r"Scripts/Link_analysis/matrix_adjacence.py" 
descriptif_script = r"Scripts/Text_mining/descriptive_analysis.py"


 
def main():
    print("Pipeline launch : ")
    
    # 0/ User choices
    do_text_mining = input("Run Step 2 (Text Mining)? (yes/no): ").lower() == 'yes'
    do_link_analysis = input("Run Step 3 (Link Analysis)? (yes/no): ").lower() == 'yes'

    # 1/ step 1: collection and cleaning
    if run_scraper:
        print("\n step 1.a : Scraping :")
        launch_scraping()
        
        print("\n step 1.b : Data Cleaning :")
        try:
            subprocess.run([sys.executable, cleaning_script], check=True)
            print("cleaning completed")
        except Exception as e:
            print(f"cleaning error: {e}")
            return
    else:
        print("\n step 1 : loading existing data")

    # 2/ step 2 : text mining
    if do_text_mining:
        print("\n step 2 : text mining analysis :")
        try:
            run_descriptive = input("Run descriptive analysis? (yes/no): ").lower() == 'yes'
            run_semantic = input("Run semantic analysis? (yes/no): ").lower() == 'yes'

            # 2.a : core text mining (TF-IDF matrices & clustering)
            print("Running core text mining :")
            launch_text_mining()
            
            # 2.b : descriptive analysis 
            if run_descriptive:
                print("Running descriptive analysis :")
                subprocess.run([sys.executable, descriptif_script], check=True)
            else:
                print("\n skipping descriptive analysis")
            
            # 2.c : semantic analysis 
            if run_semantic: 
                print("Running semantic analysis :")
                subprocess.run([sys.executable, semantic_script], check=True)
            else:
                print("\n skipping semantic analysis")

            print("Text mining process completed")
        except Exception as e:
            print(f"Text Mining error: {e}")
            return
    else:
        print("\n skipping step 2")

    # step 3 : link analysis
    if do_link_analysis:
        print("\n step 3 : link analysis :")
        try:
            # 3.a : constructing the adjacency matrix first
            subprocess.run([sys.executable, matrix_adjacency_script], check=True)
            
            # 3.b : link analysis calculations
            launch_link_analysis()
            print("Link analysis completed")
        except Exception as e:
            print(f"Link analysis error: {e}")
    else:
        print("\n skipping step 3")

    print("All steps completed successfully")

if __name__ == "__main__":
    main()