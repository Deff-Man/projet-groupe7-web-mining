import time
import pandas as pd
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse

url = "https://www.apple.com/apple-arcade/" 

#driver setup
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

#Nettoie une chaîne de caractères en supprimant les espaces superflus.
def clean_text(text):
    if not text: return "NA"
    return re.sub(r'\s+', ' ', text).strip()

def run_apple_arcade(driver) :
    try:
        print(f"Opening URL: {url}")
        driver.get(url)
        time.sleep(5) 
        
        #Scroll to bottom to ensure elements load 
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);") 
        time.sleep(3) 

        domain = urlparse(url).netloc
        site_name = "Apple Arcade" 
        
        data = []
        
        # On the Arcade page, the FAQ is often in a section with the class ‘accordion’ or ‘faq’.
        questions_elements = driver.find_elements(By.XPATH, "//li[contains(@class, 'accordion-item')]//h3")
        
        if not questions_elements:
            #if the first one doesn't work
                questions_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'accordion-item')]//h3")

            # Filters empty questions
        questions_elements = [q for q in questions_elements if len(q.text.strip()) > 5]
        
        main_window_handle = driver.current_window_handle

        for index, q_element in enumerate(questions_elements):
            try:
                #Question
                question_text = clean_text(q_element.text)
                

                #Opening
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", q_element)
                    driver.execute_script("arguments[0].click();", q_element)
                    time.sleep(1)
                except:
                    pass
                list_item = q_element.find_element(By.XPATH, "./ancestor::li[1]")
                
                #extraction 
                script_extract_data = """
                var li = arguments[0];
                var h3 = li.querySelector('h3');
                
                // Chercher le contenu (div spécifique ou tout le texte)
                var contentDiv = li.querySelector('.accordion-content, .b-text');
                
                var answerText = "";
                var linksData = [];
                
                // Extraction du texte
                if (contentDiv) {
                    answerText = contentDiv.textContent.trim();
                    var allLinks = contentDiv.querySelectorAll('a');
                } else {
                    // Fallback: tout le texte du LI moins le titre
                    var fullText = li.textContent;
                    var titleText = h3 ? h3.textContent : "";
                    answerText = fullText.replace(titleText, "").trim();
                    var allLinks = li.querySelectorAll('a');
                }
                
                // Extraction des liens
                if (allLinks) {
                    allLinks.forEach(link => {
                        // Ignorer les liens qui sont dans le titre (boutons d'ouverture)
                        if (h3 && !h3.contains(link) && link.href) {
                            linksData.push({
                                'href': link.href,
                                'text': link.textContent.trim()
                            });
                        }
                    });
                }
                
                return {
                    'answer': answerText,
                    'links': linksData
                    };
                    """
                    
                extracted_data = driver.execute_script(script_extract_data, list_item)
                
                answer_text = clean_text(extracted_data['answer'])
                raw_links = extracted_data['links']
                
                link_anchor_texts = []
                link_page_titles = []

                #Handling links found by JS
                if raw_links:
                    print(f"  > Found {len(raw_links)} links.")
                    for link_obj in raw_links:
                        href = link_obj['href']
                        anchor = link_obj['text']
                        
                        if href and href.startswith("http"):
                            link_anchor_texts.append(anchor if anchor else "Image/Link")
                            
                            # Visit the link for the title
                            try:
                                driver.execute_script("window.open(arguments[0]);", href)
                                driver.switch_to.window(driver.window_handles[-1])
                                time.sleep(2.5) 
                                page_title = driver.title.strip()
                                link_page_titles.append(page_title if page_title else "No Title")
                                driver.close()
                                driver.switch_to.window(main_window_handle)
                            except:
                                link_page_titles.append("Error Loading")
                                if len(driver.window_handles) > 1:
                                    driver.close()
                                    driver.switch_to.window(main_window_handle)

                #Backup
                data.append({
                    "site_name": site_name,
                    "url": url,
                    "question": question_text,
                    "answer": answer_text,
                    "category": "NA", # No category
                    "internal_link": 1 if link_page_titles else 0,
                    "link_name": ", ".join(link_anchor_texts) if link_anchor_texts else "NA",
                    "linked_page_title": ", ".join(link_page_titles) if link_page_titles else "NA"
                })
                
            except Exception as e:
                print(f"Error processing question {index}: {e}")
                continue
    except Exception as e:
        print(f"Global error: {e}")
    
    return pd.DataFrame(data)
