import pandas as pd
import numpy as np
import re
import string
import nltk
import matplotlib.pyplot as plt
import networkx as nx
import matplotlib
from collections import Counter
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
matplotlib.use('TkAgg') 

# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('wordnet')
# nltk.download('averaged_perceptron_tagger')

def get_wordnet_pos(word):
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {"J": wordnet.ADJ,
                "N": wordnet.NOUN,
                "V": wordnet.VERB,
                "R": wordnet.ADV}
    return tag_dict.get(tag, wordnet.NOUN)

#TOKENISAION PROCESS :
#retrieve the list of English stopwords (words to ignore) and add “'s”
stop_words = list(set(stopwords.words('english'))) + ["'s"]
brand_names = ['adobe','sap','notion', 'dropbox', 'salesforce', 'zoom', 'cisco', 'ibm', 'docusign', 'docker','nvidia','asana', 'airbnb', 'apple','github','pinterest','proton', 'telegram']
stop_words.extend(brand_names)

#to reduce words to their roots
lemmatizer = WordNetLemmatizer()

def extract_tokens(text):
    #words in lowercase letters
    text = text.lower()

    # remove the numbers.
    text = re.sub(r'\d+', '', text)
    text = text.strip()                  

    #split the sentence into a list of words
    tokens = nltk.word_tokenize(text)
    tokens = [token for token in tokens if token not in string.punctuation]

    tokens = [token for token in tokens if token not in stop_words and token not in ['yes', 'cdc', 'new', 'one', 'may']]
    tokens = [token for token in tokens if nltk.pos_tag([token])[0][1] not in ['RB', 'RBR', 'RBS', 'UH']]
            
           
    tokens = [lemmatizer.lemmatize(token, get_wordnet_pos(token)) for token in tokens]
    tokens = [token for token in tokens if len(token) > 2 and wordnet.synsets(token)]
    return tokens

def build_dictionnary_from_excel(dataframe, column_name):
    documents = {}
   
    # We go through each line of the Excel file
    for index, row in dataframe.iterrows():
        # A unique identifier is created for each line (e.g., doc_0, doc_1).
        doc_id = f"doc_{index}"
        # Extract the content of the target column
        content = row[column_name]
        # We tokenize and store in the dictionary
        documents[doc_id] = extract_tokens(content)
    return documents

def build_matrix(documents):
    # 1/ create a sorted list of all unique tokens across all documents 
    all_tokens = sorted(list(set([token for tokens in documents.values() for token in tokens])))
    token_id = {token: i for i, token in enumerate(all_tokens)}
    n = len(all_tokens)
    
    # 2/ Initialize an empty matrix 
    adj_matrix = np.zeros((n, n), dtype=int)
    
    # 3/ fill the matrix
    for doc_id,tokens in documents.items():
        unique_tokens = list(set(tokens))
        
        for i in range(len(unique_tokens)):
            for j in range(i + 1, len(unique_tokens)):
                token_a = unique_tokens[i]
                token_b = unique_tokens[j]
                
                idx_a = token_id[token_a]
                idx_b = token_id[token_b]
                
                # increment the connection weight 
                adj_matrix[idx_a, idx_b] += 1
                adj_matrix[idx_b, idx_a] += 1
                
    # 4/ convert the numpy matrix into a pd dataframe
    df_adj = pd.DataFrame(adj_matrix, index=all_tokens, columns=all_tokens)
    return df_adj

# main
path = r"C:\Users\User\Desktop\Master 1\Web mining\faq_clean.csv"
df = pd.read_csv(path)

# combine 'question' and 'answer' columns into a column
df['full_text'] = df['question'].astype(str) + " " + df['answer'].astype(str)
documents = build_dictionnary_from_excel(df, 'full_text')

# count frequency
list_tokens = [token for tokens in documents.values() for token in tokens]
token_counts = Counter(list_tokens)

# identify tokens that appear at least 3 times across the corpus
frequent_tokens = {token for token, count in token_counts.items() if count >= 3}

# filter documents
filtered_documents = {}
for doc_id, tokens in documents.items():
    filtered_tokens = [token for token in tokens if token in frequent_tokens]
    if filtered_tokens: 
        filtered_documents[doc_id] = filtered_tokens

# build matrix
matrice_adjacente = build_matrix(filtered_documents)
matrice_adjacente[matrice_adjacente < 10] = 0
mots_actifs = matrice_adjacente.columns[matrice_adjacente.sum(axis=0) > 0]
matrice_adjacente = matrice_adjacente.loc[mots_actifs, mots_actifs]
 
matrice_binaire = (matrice_adjacente >= 10).astype(int)

# export
export_path_matrix_weighted = r"C:\Users\User\Desktop\Master 1\Web mining\matrice_adjacence_ponderee.csv"
export_path_matrix_binary = r"C:\Users\User\Desktop\Master 1\Web mining\matrice_adjacence_binaire.csv"

matrice_adjacente.to_csv(export_path_matrix_weighted)
matrice_binaire.to_csv(export_path_matrix_binary)

# export nodes and edges

nodes = pd.DataFrame([{'Id': token, 'Label': token, 'Count': token_counts[token]} for token in matrice_adjacente.index])
edges_list = []
tokens_list = list(matrice_adjacente.index)
for i in range(len(tokens_list)):
    for j in range(i + 1, len(tokens_list)):
        weight = matrice_adjacente.iloc[i, j]
        if weight >= 10:
            edges_list.append({
                'Source': tokens_list[i],
                'Target': tokens_list[j],
                'Weight': weight})

edges = pd.DataFrame(edges_list)

# output file paths
export_path_nodes = r"C:\Users\User\Desktop\Master 1\Web mining\nodes.csv"
export_path_edges = r"C:\Users\User\Desktop\Master 1\Web mining\edges.csv"

nodes.to_csv(export_path_nodes, index=False)
edges.to_csv(export_path_edges, index=False)

