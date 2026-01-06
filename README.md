# Web Mining Project
# Comparative Analysis of Tech FAQ Pages

This project was developed as part of the **Web Mining** course at UCLouvain FUCaM Mons. It applies advanced data collection and analysis techniques to study user concerns and corporate responses through FAQ pages of major technology companies.

## Authors
* **Matthieu Beaumont**
* **Manon Deffontaines**
* **Zoé Vandevelde**

---

## Project Overview
The objective is to analyze how technology companies address user needs by extracting, processing, and modeling data from their Frequently Asked Questions (FAQ). The project is divided into three main phases:

1. **Data Collection (Scraping):** Automated extraction of raw data from FAQ pages of various tech companies.
2. **Text Mining:**  Linguistic preprocessing (lemmatization).
    * Vectorization (TF-IDF and SBERT).
    * Descriptive and semantic analysis.
    * Theme identification through K-Means clustering.
3. **Link Analysis:** Creation of a non-oriented semantic graph based on concept co-occurrences.
    * Topology analysis (pivot nodes, bridge links).
    * Proximity studies using centrality and similarity measures.

---

## Project Structure

The project is organized into a main orchestrator and a modular script architecture:

### A. Main 
* `main.py` : central orchestrator for the entire pipeline.
* `README.md` : project documentation.
* `.gitignore` : instructions for Git to ignore temporary files (like `__pycache__`).

### B. Scripts 
The core logic is divided into three specialized modules:

#### 1. Scraping & Data Cleaning (`Scripts/Scraping/`)
* **data_collection_merging/** : Main folder for web extraction.
    * `scraping.py` : Main merging script.
    * `Manon_scrapping.py`, `Matthieu_scraping.py`, `put_together.py` : individual scraper modules.
    * Company-specific scrapers: `zoom_scraping`, `Cisco_scraping`, `Dropbox_scraping`, etc.
* **data_cleaning/** :
    * `cleaning_data.py` : Automated preprocessing and normalization of raw data.

#### 2. Text Mining (`Scripts/Text_mining/`)
* `text_mining.py` : Core Text mining script (TF-IDF & Clustering).
* `descriptive_analysis.py` : Visual analysis (Wordclouds, Treemaps).
* `semantic_textmining_application.py` : Topic modeling (NMF).
  
#### 3. Link Analysis (`Scripts/Link_analysis/`)
* `matrix_adjacence.py` : Construction of the co-occurrence matrix.
* `link_analysis_.py` : Network metrics (Centrality, PageRank) and graph theory analysis.


### C. Data 
* `Data/` : Storage for raw (`faq_commun.csv`) and processed (`faq_clean.csv`) data.

### D. Results
* `Results/` : Exported analysis files (Excel sheets, Plots and Matrices).

--- 

# User Guide 
## 1. Installation & Setup
Ensure you have Python Python installed. Clone the repository and install the necessary dependencies.

## 2. Execution Flow
The entire workflow (Scraping, Text Mining and Link Analysis) is managed by a single central orchestrator (main.py) to ensure full replicability. To launch the project analysis, run the following command in your terminal:  `main.py/`

The script is interactive and will prompt you to choose which analysis modules to execute. It manages the following stages:

* ### Step 1 : Data Collection & Cleaning :
  If enabled, it launches automated scraping followed by a cleaning script (cleaning_data.py) via a subprocess.
* ### Step 2: Text Mining:
  This module performs core processing (TF-IDF & Clustering). Users can interactively choose to run additional Descriptive Analysis (wordclouds/visuals) annd/or Semantic Analysis (NMF topic modeling).
* ### Step 3: Link Analysis:
* The pipeline first constructs the required adjacency matrix (matrix_adjacence.py) before launching the final network metrics and graph calculations.

In the `main.py/` script, run_scraper is set to False by default. A pre-collected dataset is already provided to save you approximately 2 hours of processing time. If you wish to perform a fresh data collection, simply set the run_scraper variable to True in `main.py/`.

## 3. Update these paths to match your local machine environment
* data_raw = r"C:\Users\...\faq_commun.csv"
* data_clean = r"C:\Users\...\faq_clean.csv"

---
# Method

# Part A: Data Collection & Cleaning

## 1. Organization
The web scraping phase was organized collaboratively to allow parallel development. 
Each group member managed a dedicated scraping directory:

* Manon_scrapping
* Matthieu_scraping
* Zoe_scraping

Within each personal directory, several sub-folders are implemented. Each sub-folder contains a specific Python script dedicated to scraping a particular website and extracting relevant data points.

## 2. Collected Data Fields
For every FAQ entry, the following information is extracted:

* site_name: The name of the website.
* url: The source URL.
* question: The text content of the question.
* answer: The text content of the response.
* category: The category the question belongs to (as defined by the source).
* internal_link: A binary variable (1 if a link is present in the answer, 0 otherwise).
* link_name: The specific word or phrase acting as the hyperlink.
* linked_page_title: The title of the page targeted by the internal link.

## 3. Execution Logic & Merging
To ensure a smooth workflow, the aggregation follows a hierarchical structure:

* Personal Runners: Each personal directory contains a runner script that executes all site-specific scrapers within that folder to generate an intermediate dataset.
* Global Orchestrator: A global scraping script (`scraping.py/`) calls the three personal runners and aggregates all intermediate results into a single final dataset in CSV format.

## 4. Data Cleaning

The pipeline includes an advanced cleaning script (`cleaning_data.py/`) that deduplicates entries, normalizes encoding issues, and uses deep_translator to convert all non-English content into English.

---
# Part B: Text Mining 

## 1. Overview

This phase converts cleaned FAQ text into structured numerical data for pattern discovery. It combines traditional NLP techniques with advanced machine learning models (SBERT, GloVe, NMF) to identify themes and calculate document similarities.
The pipeline processes the `faq_clean.csv` file through several specialized scripts:
  1. **Core Text Mining** (`text_mining.py`): Handles lemmatization, vectorization (TF-IDF/BERT), and clustering.
  2. **Descriptive Analysis** (`descriptive_analysis.py`): Generates visual insights like WordClouds, Bigrams and Intent Treemaps.
  3. **Semantic Analysis** (`semantic_textmining_application.py`): Uses Non-negative Matrix Factorization (NMF) for advanced topic modeling.

## 2. Technical Methodology

1. **Text Preprocessing & Tokenization** : To ensure high-quality analysis, the text is standardized using the following steps:
   * **Lemmatization**: Words are reduced to their root form.
   * **Filtering**: Removal of stop words, brand names (Adobe, IBM, etc.), numbers, and short words.
   * **Thresholding**: Terms appearing in fewer than 3 documents or more than 50% of the corpus are filtered out to remove noise and non-discriminant words.
     
2. **Vectorization & Clustering** : The project utilizes multiple embedding techniques to represent FAQ questions:
   * **TF-IDF Matrix**: Captures term importance relative to the corpus.
   * **SBERT (Sentence-BERT)**: Uses the all-MiniLM-L6-v2 model to capture deep semantic meaning.
   * **K-Means Clustering**: Documents are grouped into themes. The Elbow Method and Silhouette Scores are used to determine the optimal number of clusters.
     
3. **Semantic & Topic ModelingGloVe Embeddings**:
   * **Leverages pre-trained vectors** (glove-wiki-gigaword-50) to analyze word-level semantic relationships.
   * **NMF** (Non-negative Matrix Factorization): Decomposes the TF-IDF matrix into document-topic and topic-word distributions.
     
4. **Visualizations & Insights** : The following tools are used to interpret the results:
   * **WordClouds & Bigrams**: Visual representations of the most frequent terms and word pairs.
   * **Intent Treemap**: Categorizes questions by their starting keyword (e.g., "How" → Method, "Can" → Possibility).
   * **Heatmaps**: Displays cosine similarity between different companies based on their FAQ content distribution.

---
# Part C: Link Analysis 

## 1. Overview
This final phase converts extracted semantic relationships into a structured network. It allows for the study of the knowledge topology within the FAQs, identifying dominant themes and understanding how information flows across different tech companies.

## 2. Code Objective
The Link Analysis module transforms text mining outputs into structured graphs through two main stages:

* **Adjacency Matrix Construction** (`matrix_adjacence.py`)
* **Network Analysis** (`link_analysis_.py`):

## 3. Core Technical Features

### A. Basic Graph Matrices

* **Degree & Transition Matrices**
* **Laplacian & Pseudoinverse**
  
### B. Centrality & Distance Measures

   * **PageRank (Power Iteration)**
   * **Betweenness & Closeness**
   * **Eccentricity & Radius**

### C. Similarity & Link Prediction

   * **Jaccard Similarity**
   * **Preferential Attachment**
   * **Common Neighbor**
     
### D. Subgroup & Structural Analysis
   * **Clique Analysis**
   * **K-core Decomposition**
   * **Articulation Points & Bridges**
