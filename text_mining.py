import pandas as pd
import numpy as np
import re
import string
from collections import Counter
import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from sentence_transformers import SentenceTransformer
import gensim.downloader as api
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib
import matplotlib.pyplot as plt
from sklearn.metrics import silhouette_score
matplotlib.use('TkAgg')
import seaborn as sns

#nltk.download('punkt')
#nltk.download('punkt_tab')
#nltk.download('stopwords')

#for lemmatization:
#nltk.download('wordnet')
#nltk.download('omw-1.4')
#nltk.download('averaged_perceptron_tagger_eng')

#for advanced lemmatization:
def get_wordnet_pos(word):
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {"J": wordnet.ADJ,
                "N": wordnet.NOUN,
                "V": wordnet.VERB,
                "R": wordnet.ADV}
    return tag_dict.get(tag, wordnet.NOUN)
 
#TOKENISATION PROCESS :
#retrieve the list of English stopwords (words to ignore) and add “'s”
stop_words = list(set(stopwords.words('english'))) + ["'s"]
brand_names = ['adobe','sap','notion', 'dropbox', 'salesforce', 'zoom', 'cisco', 'ibm', 'docusign', 'docker','nvidia','asana', 'airbnb', 'apple','github','pinterest','proton', 'telegram']
stop_words.extend(brand_names)

#to reduce words to their roots
lemmatizer = WordNetLemmatizer()
def extract_tokens(text):
    # words in lowercase letters
    text = text.lower()

    # remove the numbers
    text = re.sub(r'\d+', '', text)  
    text = text.strip()                  

    # split the sentence into a list of words
    tokens = nltk.word_tokenize(text)
    # remove punctuation
    tokens = [token for token in tokens if token not in string.punctuation]
    # remove stopwords
    tokens = [token for token in tokens if token not in stop_words and token not in ['yes', 'cdc', 'new', 'one', 'may']]
    # exclude adverbs (RB, RBR, RBS) and interjections (UH)
    tokens = [token for token in tokens if nltk.pos_tag([token])[0][1] not in ['RB', 'RBR', 'RBS', 'UH']]
    # advanced lemmatization with context (verb, noun, adjective)    
    tokens = [lemmatizer.lemmatize(token, get_wordnet_pos(token)) for token in tokens]
    # we keep only words longer than 2 characters and ensures they exist in the WordNet dictionary
    tokens = [token for token in tokens if len(token) > 2 and wordnet.synsets(token)]
    return tokens

def build_dictionnary_from_excel(dataframe, column_name):
    documents = {}

    # we go through each line of the excel file
    for index, row in dataframe.iterrows():
        # a unique identifier is created for each line (e.g., doc_0, doc_1).
        doc_id = f"doc_{index}"
        # we extract the content of the target column
        content = row[column_name]
        # we tokenize and store in the dictionary
        documents[doc_id] = extract_tokens(content)
    return documents

def build_dictionnary_aggregated(dataframe, group_col, text_col):
    # 1/ group by site and join all questions separated by a space
    df_grouped = dataframe.groupby(group_col)[text_col].apply(lambda x: ' '.join(x)).reset_index()
    documents = {}

    # 2/ iterate through this new grouped dataframe
    for index, row in df_grouped.iterrows():
        # the identifier becomes the site name (e.g., "Adobe", "Notion")
        doc_id = row[group_col]
        content = row[text_col]

        # 3/ Use the existing tokenization function
        documents[doc_id] = extract_tokens(content)    
    return documents

# analyzes word distribution to help to choose the min threshold
def analyze_thresholds(documents_dict):
    # convert each document's token list to a set, flatten the list of sets into one long list
    all_unique_doc_tokens = [token for tokens in documents_dict.values() for token in set(tokens)]
    # count occurrences
    doc_freq_counter = Counter(all_unique_doc_tokens)
   
    total_docs = len(documents_dict)
   
    # a//minimum thresholds
    # we test how many words remain if we filter out rare words
    thresholds = [1, 2, 3, 4, 5]
    results = []
 
    freq_values = list(doc_freq_counter.values())
 
    for t in thresholds:
        # count words that appear in at least t documents
        remaining_words = sum(1 for f in freq_values if f >= t)
        results.append({'Threshold': t, 'Remaining words': remaining_words})
       
    # Display the results table
    print("\n Minimum threshold analysis")
    df_results = pd.DataFrame(results)
    print(df_results)
   
    # b// maximum thresholds
    # create a DataFrame from the counter, sorted by frequency
    df_dist = pd.DataFrame.from_dict(doc_freq_counter, orient='index', columns=['Nb_Documents'])
    df_dist = df_dist.sort_values(by='Nb_Documents', ascending=False)
   
    # prepare data for plotting
    y_values = df_dist['Nb_Documents'].values
    x_values = range(len(y_values))
   
    # plot
    plt.figure(figsize=(12, 6))
   
    # plot the curve
    plt.plot(x_values, y_values, color='blue', linewidth=2, label='Word Distribution')
   
    # add the suggested max threshold line (e.g : 50% of documents)
    threshold_val = total_docs * 0.5
    plt.axhline(y=threshold_val, color='red', linestyle='--', label=f'Suggested max threshold (50% = {int(threshold_val)} docs)')
   
    # graph
    plt.title("Global word frequency distribution ", fontsize=14)
    plt.xlabel("Word rank", fontsize=12)
    plt.ylabel("Number of documents", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
   
    # fill under the curve
    plt.fill_between(x_values, y_values, color='blue', alpha=0.1)
    plt.tight_layout()
    plt.show()

# matrix term document :
def build_term_document_matrix(documents):
    # 1/ build a vocabulary (unique terms across all documents)
    vocabulary = set(token for tokens in documents.values() for token in tokens)
    # 2/ count term frequencies for each document
    term_frequencies = {doc: Counter(tokens) for doc, tokens in documents.items()}
    # 3/ construct the term-document matrix
    td_matrix = pd.DataFrame(
        {term: [term_frequencies[doc].get(term, 0) for doc in documents] for term in vocabulary},
        index=documents.keys())
   
    # 4a/ filter terms that appear in fewer than two documents
    document_frequency = (td_matrix > 0).sum(axis=0)
    filtered_td_matrix = td_matrix.loc[:, document_frequency >= 3]
 
    # 4b/ filter terms that appear in a lot of documents
    document_frequency = (filtered_td_matrix > 0).sum(axis=0)
    filtered_td_matrix = filtered_td_matrix.loc[:, document_frequency < 0.5 * len(documents)]
 
    # vocabulary remaining after modification
    updated_vocabulary = filtered_td_matrix.columns.tolist()
 
    return filtered_td_matrix
 
# Matrix TF-IDF :
def compute_tf_idf(filtered_td_matrix):
    # total tokens per document (row)
    row_sums = filtered_td_matrix.sum(axis=1)  
    # replace 0 with 1 to prevent division by zero for empty documents
    row_sums_modified = row_sums.replace(0, 1)
    # each value in a row is divided by the sum of that row.
    tf = filtered_td_matrix.div(row_sums_modified, axis=0)
    # number of documents containing each term (column)
    df = (filtered_td_matrix > 0).sum(axis=0)  
    # number of documents (number of lines)
    N = filtered_td_matrix.shape[0]  
    # calculation of the IDF
    idf = np.log((N) / (df))
    # final TF-IDF calculation
    tf_idf = tf.mul(idf, axis=1)
    return tf_idf
 
# Matrix Bert
def compute_bert_embeddings(texts, model_name ="all-MiniLM-L6-v2"):
    # load SBERT model
    model = SentenceTransformer(model_name)
    # compute embeddings
    embeddings = model.encode(list(texts), normalize_embeddings=True)
    return embeddings
   
def compute_bert_similarity(dataframe, column_name) :
    corpus = {}
    for index, row in dataframe.iterrows():
        corpus[f"doc_{index}"] = str(row[column_name])
   
    doc_names = list(corpus.keys())
    documents = list(corpus.values())
    embeddings = compute_bert_embeddings(embeddings)
    # compute cosine similarity matrix
    similarity_matrix_bert = cosine_similarity(embeddings)
    # create DataFrame
    similarity_df_bert = pd.DataFrame(similarity_matrix_bert,index=doc_names,columns=doc_names)
    return similarity_df_bert
 
def perform_sbert_clustering(dataframe, text_col, k=5, output_path=None, embeddings = None):
    print(f"\n Starting SBERT clustering (k={k}) : ")
   
    # 1/ SBERT encoding
    if embeddings is None :
            texts = dataframe[text_col].tolist()
            embeddings = compute_bert_embeddings(texts)
 
    # 2/ K-Means clustering
    print("grouping documents (K-Means) :")
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(embeddings)
    clusters = kmeans.labels_
   
    # 3/ cluster naming (using TF-IDF to find keywords)
    print("identifying keywords for each theme :")
    # we recalculate TF-IDF locally
    docs = build_dictionnary_from_excel(dataframe, text_col)
    matrix = build_term_document_matrix(docs)
    tf_idf = compute_tf_idf(matrix).fillna(0)
   
    cluster_names = {}
    for i in range(k):
        indices = [idx for idx, c in enumerate(clusters) if c == i]
        if indices:
            relevant_tfidf = tf_idf.iloc[indices]
            mean_score = relevant_tfidf.mean(axis=0)
            top_words = mean_score.sort_values(ascending=False).head(4).index.tolist()
            name = " / ".join(top_words)
        else:
            name = "Miscellaneous"
        cluster_names[i] = name
   
    # 4/ creating final dataframe
    df_result = dataframe.copy()
    df_result['Cluster_ID'] = clusters
    df_result['Theme_Estime'] = [cluster_names[c] for c in clusters]
   
    # 5/ export excel
    if output_path:
        df_result.sort_values(by='Cluster_ID').to_excel(output_path, index=False)
        print(f" excel file generated: {output_path}")
       
    return df_result, embeddings, tf_idf
 
def build_semantic_glove_matrix(docs_dictionary, docs_by_site, n_clusters=3):
    try:
        # load Glove vectors
        model = api.load("glove-wiki-gigaword-50")
    except Exception as e:
        print("GloVe loading error.")
        return None, None 
 
    # filter vocabulary to keep only words present in GloVe
    my_vocabulary = set()
    for tokens in docs_dictionary.values():
        for token in tokens:
            if token in model:
                my_vocabulary.add(token)
   
    # list of vectors corresponding to the filtered vocabulary
    my_vocabulary = list(my_vocabulary)
    vectors = [model[word] for word in my_vocabulary]
    print(f"Words analyzed : {len(my_vocabulary)}")
 
    # clustering with KMeans to identify themes
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    km.fit(vectors)
    
    # creation of a word -> theme dictionary
    word_to_concept = dict(zip(my_vocabulary, km.labels_))


    df_lexique = pd.DataFrame(list(word_to_concept.items()), columns=['Mot', 'Cluster_ID'])
    df_lexique = df_lexique.sort_values(by='Cluster_ID')

    col_names = []
    for i in range(n_clusters):
        words = df_lexique[df_lexique['Cluster_ID'] == i]['Mot'].tolist()
        preview = ", ".join(words[:10])
        print(f"Theme {i+1} : {preview}...")
        col_names.append(f"Theme {i+1}")
       
    # construction of the Site x Theme matrix    
    def get_site_concepts_count(text_tokens):
        # count how many words from each theme are present
        concepts_count = np.zeros(n_clusters)
        for token in text_tokens:
            if token in word_to_concept:
                cluster_id = word_to_concept[token]
                concepts_count[cluster_id] += 1
        return concepts_count
 
    site_data = {}
    for site, tokens in docs_by_site.items():
        site_data[site] = get_site_concepts_count(tokens)
 
    # creating the DataFrame
    df_count = pd.DataFrame.from_dict(site_data, orient='index', columns=col_names)
   
    # Return BOTH tables: the site matrix AND the word lexicon
    return df_count, df_lexique

def process_and_plot_themes(input_data, output_path_percentage=None):
    # Load Data
    if isinstance(input_data, str):
        df = pd.read_excel(input_data)
    else:
        df = input_data.copy()

    if 'Unnamed: 0' in df.columns:
        df = df.rename(columns={'Unnamed: 0': 'Site'})
        df = df.set_index('Site')
    elif 'Site' in df.columns:
        df = df.set_index('Site')

    if pd.api.types.is_numeric_dtype(df.index):
        df = df.set_index(df.columns[0])

    df.index.name = "Entreprises" 
  
    df_numeric = df.select_dtypes(include=['number'])
    row_sums = df_numeric.sum(axis=1)
    df_percent = df_numeric.div(row_sums, axis=0).fillna(0)

    # Save Excel
    if output_path_percentage:
        df_percent.to_excel(output_path_percentage)
        print(f"Percentages saved : {output_path_percentage}")

    # graph preparation
    noms_themes = {
        "Theme 1": "T1: Vie d'entreprise / Communauté",     
        "Theme 2": "T2: Légale & Conformité",     
        "Theme 3": "T3: Usage Produit & Outils",  
        "Theme 4": "T4: Tech & Développement ",      
        "Theme 5": "T5: Finance & Facturation"     
    }
    df_plot = df_percent.rename(columns=noms_themes)

    #Bar Chart
    plt.figure(figsize=(14, 8))
    df_plot.plot(kind='bar', stacked=True, colormap='viridis', figsize=(14, 8), width=0.8)
    plt.title("Répartition Thématique par Entreprise", fontsize=16)
    plt.xlabel("Entreprises", fontsize=12)
    plt.ylabel("Proportion", fontsize=12)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()

    # Heatmap 
    sim_matrix = cosine_similarity(df_plot)
    similarity_df = pd.DataFrame(sim_matrix, index=df_plot.index, columns=df_plot.index)

    plt.figure(figsize=(12, 10))
    sns.heatmap(similarity_df, annot=True, cmap='coolwarm', fmt=".2f")
    plt.title("Matrice de Similarité", fontsize=16)
    plt.tight_layout()
    plt.show()
    
    return df_percent

def plot_similarity_matrix(similarity_df, title = "Document Similarity Matrix"):
    # Plot the similarity matrix
    similarity_df = similarity_df.fillna(0)
    plt.figure(figsize=(8, 6))
    plt.imshow(similarity_df, interpolation='nearest', cmap='viridis')
    plt.colorbar(label='Cosine Similarity')
    plt.title(title)
    plt.xticks(ticks=range(len(similarity_df.columns)), labels=similarity_df.columns, rotation=45)
    plt.yticks(ticks=range(len(similarity_df.index)), labels=similarity_df.index)
    plt.xlabel('Documents')
    plt.ylabel('Documents')
 
    # optionally, annotate the cells with similarity values
    for i in range(len(similarity_df)):
        for j in range(len(similarity_df)):
            plt.text(j, i, f"{similarity_df.iloc[i, j]:.3f}", ha='center', va='center', color='white')
 
    plt.tight_layout()
 
# plots the elbow curve to help identify the optimal number of clusters
def plot_elbow_method(vectors, max_k=15):
   
    inertias = []
    K_range = range(1, max_k + 1)
   
    print(f"Calculating the optimal number of clusters (testing from 1 to {max_k}) :")
   
    for k in K_range:
        # testing KMeans for each value of k
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(vectors)
        # inertia measures how compact the clusters are
        inertias.append(km.inertia_)
       
    # Plotting the results
    plt.figure(figsize=(10, 6))
    plt.plot(K_range, inertias, 'bx-')
    plt.xlabel('Number of clusters (k)')
    plt.ylabel('Inertia (Distortion)')
    plt.title('The Elbow Method for Finding the Optimal k')
    plt.xticks(K_range)
    plt.grid(True)
    plt.show()
 
def plot_silhouette_method(vectors, max_k=15):
    scores = []
    K_range = range(2, max_k + 1)
 
    print(f"Calculating silhouette scores (testing from k=2 to {max_k}) :")
   
    for k in K_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(vectors)
        score = silhouette_score(vectors, labels)
        scores.append(score)
        print(f"k={k}, score={score:.4f}")
 
    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(K_range, scores, 'ro-')
    plt.xlabel('Number of clusters (k)')
    plt.ylabel('silhouette score')
    plt.title('silhouette method for finding optimal k')
    plt.xticks(K_range)
    plt.grid(True, alpha=0.3)
    plt.show()
 
#MAIN EXECUTION :
def main ():
    try :
        file_path = r"C:\Users\Utilisateur\Desktop\Master 1\Q1 part 2\Web mining\projet\faq_clean.csv"
        base_path = r"C:\Users\Utilisateur\Desktop\Master 1\Q1 part 2\Web mining\projet\\"
        df = pd.read_csv(file_path)
   
        # 1/ dictionary of questions
        docs = build_dictionnary_from_excel(df, 'question')
 
        # 2/ analyze thresholds
        analyze_thresholds(docs)
 
        # 3/ term-document matrix
        matrix = build_term_document_matrix(docs)
        print("Filtered term-document matrix:")
        print(matrix)
        matrix.to_excel(base_path + "1_matrix_term_doc.xlsx")
 
        # 4/ TF-IDF matrix
        tf_idf_matrix = compute_tf_idf(matrix)
        print("Matrix TF-IDF :")
        print(tf_idf_matrix)
        tf_idf_matrix.to_excel(base_path + "2_matrix_tfidf_global.xlsx")
 
        # 5/ aggregation by site
        docs_by_site = build_dictionnary_aggregated(df, 'site_name', 'question')
        print(f"Number of identified sites : {len(docs_by_site)}")
        print("Sites :", list(docs_by_site.keys()))
 
        # 5a/ term-document matrix by site
        matrix_site = build_term_document_matrix(docs_by_site)
        print("\n filtered term-document matrix by site :")
        print(matrix_site)
        matrix_site.to_excel(base_path + "3_matrix_term_doc_par_site.xlsx")
 
        # 5b/ TF-IDF matrix by site
        tf_idf_site = compute_tf_idf(matrix_site)
        print("\n TF-IDF matrix by site :")
        print(tf_idf_site)
        tf_idf_site.to_excel(base_path + "4_matrix_tfidf_par_site.xlsx")
 
        # 6/ theme with GloVe
        df_count, df_lexique = build_semantic_glove_matrix(docs, docs_by_site, n_clusters=5)
        
        if df_count is not None:
            #Save raw data (Counts)
            print(df_count.astype(int))
            df_count.to_excel(base_path + "5_matrix_site_themes_glove.xlsx")
            
            #Save lexicon
            path_lexique = base_path + "5b_detail_mots_par_theme.xlsx"
            df_lexique.to_excel(path_lexique, index=False)
            
            #Define output path for percentage file
            path_pourcentage = base_path + "repartition_themes_pourcentage.xlsx"
            
            #Call the main processing function with raw data (df_count)
            process_and_plot_themes(df_count, output_path_percentage=path_pourcentage)

 
        # 7/ Similarity TF-IDF
        # compute the cosine similarity matrix for TF-IDF
        similarity_matrix_tfidf = cosine_similarity(tf_idf_matrix)
        similarity_df_tfidf = pd.DataFrame(similarity_matrix_tfidf, index=tf_idf_matrix.index, columns=tf_idf_matrix.index)
 
        # 8/ similarity BERT
        texts = df['question'].astype(str).tolist()
        embeddings = compute_bert_embeddings(texts)
 
        # 9/ clustering SBERT & Elbow method & Silhouette method
        plot_elbow_method(embeddings, max_k=15)
        plot_silhouette_method(embeddings, max_k=15)
        path_export_clusters = base_path + "7_resultats_clustering_themes.xlsx"
        df_result, embeddings, tf_idf_matrix = perform_sbert_clustering(df,text_col='question',k=5, output_path=path_export_clusters, embeddings=embeddings)

        # 10/ similarity calculation
        print("\n similarity analysis : ")
   
        # 10a/ SBERT similarity
        print("display sbert similarity matrix :")
        similarity_matrix_bert = cosine_similarity(embeddings)
        similarity_df_bert = pd.DataFrame(similarity_matrix_bert, index=df.index, columns=df.index)


        # optional plotting :
        #plot_similarity_matrix(similarity_df_bert)
        #plt.title("similarity sbert :")
        #plt.show()
   
        # Plot Tf-idf
        #plot_similarity_matrix(similarity_df_tfidf)
        #plt.show()
 
        # Plot BERT
        #print("Print matrix BERT :")
        #plot_similarity_matrix(similarity_df_bert)
        #plt.show()
 
        # Save to Excel
        output_path_sim = base_path + "8_comparaison_similarities_final.xlsx"
        with pd.ExcelWriter(output_path_sim) as writer:
            similarity_df_tfidf.to_excel(writer, sheet_name='TF-IDF')
            similarity_df_bert.to_excel(writer, sheet_name='BERT')
 
    except FileNotFoundError:
            print("Error: The Excel file was not found. Check the path.")
    except Exception as e:
        print(f"An error occurred: {e}")
 
if __name__ == "__main__":
    main()
    