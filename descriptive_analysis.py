import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from collections import Counter
import nltk
import re
import string
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.util import ngrams
import matplotlib
matplotlib.use('TkAgg')
import numpy as np            
import networkx as nx        
import squarify
import seaborn as sns
from sklearn.feature_extraction.text import CountVectorizer

#for advanced lemmatization:
def get_wordnet_pos(word):
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {"J": wordnet.ADJ,
                "N": wordnet.NOUN,
                "V": wordnet.VERB,
                "R": wordnet.ADV}
    return tag_dict.get(tag, wordnet.NOUN)

#TOKENISAION PROCESS :
stop_words = list(set(stopwords.words('english'))) + ["'s"]
brand_names = ['adobe','sap','notion', 'dropbox', 'salesforce', 'zoom', 'cisco', 'ibm', 'docusign', 'docker','nvidia','asana', 'airbnb', 'apple','github','pinterest','proton', 'telegram']
stop_words.extend(brand_names)

#to reduce words to their roots
lemmatizer = WordNetLemmatizer()
def extract_tokens(text):
    text = text.lower()
    text = re.sub(r'\d+', '', text)
    tokens = nltk.word_tokenize(text)
    tokens = [token for token in tokens if token not in string.punctuation]
    tokens = [token for token in tokens if token not in stop_words]
    tokens = [lemmatizer.lemmatize(token, get_wordnet_pos(token)) for token in tokens]
    return tokens

def wordcloud(tokens, title, ax):
    # list of generic technical words to exclude from the cloud
    generic_stops = ['also','how', 'can', 'get', 'use', 'find', 'way', 'make', 'go', 'see', 'want', 'take']
    tokens_finals = [t for t in tokens if t not in generic_stops and len(t) > 3]
    
    # calculate relative frequencies for proportionality
    counts = Counter(tokens_finals)
    total = sum(counts.values())
    relative_freqs = {word: count / total for word, count in counts.items()} if total > 0 else {}

    # wordcloud configuration
    wc = WordCloud(width=800, height=800, background_color='white', max_words=50, colormap='viridis',collocations=False).generate_from_frequencies(relative_freqs)
    
    ax.imshow(wc, interpolation='bilinear')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.axis('off')

# identifies the most frequent bigrams
def plot_bigrams(tokens, title, top_n=20, ax = None):
    if len(tokens) < 2:
        return

    bigrams = list(ngrams(tokens, 2))
    counts = Counter(bigrams).most_common(top_n)

    labels = [f"{b[0]} {b[1]}" for b, _ in counts]
    values = [count for _, count in counts]

    print(f"\n{title}")
    for i, (b, c) in enumerate(counts, start=1):
        print(f"{i:02d}. {b[0]} {b[1]}  :  {c}")

    labels = [f"{b[0]} {b[1]}" for b, _ in counts]
    values = [count for _, count in counts]
    if ax is None:
        plt.figure(figsize=(10, 7))
        plt.barh(labels, values, color="#1A588B")
        plt.gca().invert_yaxis()
        plt.title(title, fontsize=14)
        plt.grid(axis='x', linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.show()
    else:
        ax.barh(labels, values)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=12)
        ax.grid(axis='x', alpha=0.3)

# categorize the intent of a question based on its starting keyword
def analyze_question_structure(text):
    text = str(text).lower().strip() 
    if text.startswith(('how')):
        return 'Méthode'
    elif text.startswith(('can', 'could', 'may')):
        return 'Possibilité'
    elif text.startswith(('what', 'which', 'where', 'who', 'why')):
        return 'Information'
    elif text.startswith(('does', 'do i', 'is' 'are')):
        return 'Confirmation'
    else:
        return 'Autres formulations'

# visualize the global distribution of question intents accross a treemap
def global_treemap(dataframe):
   
    df_all = dataframe.copy()
    df_all['intent'] = df_all['question'].apply(analyze_question_structure)
    counts = df_all['intent'].value_counts()
    
    plt.figure(figsize=(14, 8))
    colors = sns.color_palette("Spectral", len(counts)) 
    
    squarify.plot(sizes=counts.values, label=[f"{l}\n({v} items)" for l, v in zip(counts.index, counts.values)], 
                  alpha=0.8, color=colors, pad=True, text_kwargs={'fontsize': 12, 'fontweight': 'bold'})
    
    plt.title("Stratégie globale des FAQ : analyse des intentions ", fontsize=16, fontweight='bold', pad=20)
    plt.axis('off')
    plt.show()

# (optional) compare the intent profiles across multiple selected companies side-by-side
def comparative_treemaps(dataframe, sites):

    n_sites = len(sites)
    fig, axes = plt.subplots(1, n_sites, figsize=(6 * n_sites, 6))
    if n_sites == 1: axes = [axes]
    
    for i, site in enumerate(sites):
        df_site = dataframe[dataframe['site_name'].str.lower() == site.lower()].copy()
        if df_site.empty: continue
        
        df_site['intent'] = df_site['question'].apply(analyze_question_structure)
        counts = df_site['intent'].value_counts()
        
        colors = sns.color_palette("viridis", len(counts))
        
        plt.sca(axes[i])
        squarify.plot(sizes=counts.values, label=[f"{l}\n{v}" for l, v in zip(counts.index, counts.values)], 
                      alpha=0.7, color=colors, pad=True, ax=axes[i], text_kwargs={'fontsize': 10})
        
        axes[i].set_title(f"Intent Profile: {site.upper()}", fontsize=13, fontweight='bold')
        axes[i].axis('off')
        
    plt.tight_layout()
    plt.show()


# create a heatmap showing how often specific words (top 20) appear together in the same question
def plot_cooccurrence_matrix(documents, top_n=20):

    text_data = [" ".join(tokens) for tokens in documents.values()]
    vectorizer = CountVectorizer(max_features=top_n)
    X = vectorizer.fit_transform(text_data)
    
    xc = (X.T * X)
    xc.setdiag(0)
    
    names = vectorizer.get_feature_names_out()
    df_cooc = pd.DataFrame(data=xc.toarray(), columns=names, index=names)

    plt.figure(figsize=(12, 10))
    sns.heatmap(df_cooc, annot=True, fmt='d', cmap='YlGnBu', cbar=True)
    plt.title(f"Matrice de Cooccurrence - Top {top_n} mots", fontsize=15, fontweight='bold')
    plt.xticks(rotation=45)
    plt.show()   

# execution
if __name__ == "__main__":
    # load data
    path = r"C:\Users\User\Desktop\Master 1\Web mining\faq_clean.csv"
    df = pd.read_csv(path)
    
    # select sites to compare
    sites_to_compare = ['Adobe', 'SAP', 'ibm' ] 
   
    # 1/ global wordcloud
    print("Global word cloud :")
    all_tokens = []
    for text in df['question']:
        all_tokens.extend(extract_tokens(text))
    
    fig_glob, ax_glob = plt.subplots(figsize=(10, 7))
    wordcloud(all_tokens, "Nuage de mots global", ax_glob)
    plt.show()

    # 2/ comparative word clouds
    if sites_to_compare:
        n_sites = len(sites_to_compare)
        print(f"Word clouds for : {', '.join(sites_to_compare)}...")
        
       # create a space adapted to the number of chosen sites
        fig_comp, axes = plt.subplots(1, n_sites, figsize=(6 * n_sites, 6))
        
        # if only one site is selected, convert axes into a list for iteration
        if n_sites == 1:
            axes = [axes]
            
        for i, site in enumerate(sites_to_compare):
            # filter data for the specific site
            site_data = df[df['site_name'].str.lower() == site.lower()]
            
            if not site_data.empty:
                site_tokens = []
                for q in site_data['question']:
                    site_tokens.extend(extract_tokens(q))
                
                title = f"FAQ : {site}\n({len(site_data)} questions)"
                wordcloud(site_tokens, title, axes[i])
            else:
                axes[i].text(0.5, 0.5, f"site '{site}'\nnot found in CSV", ha='center', va='center')
                axes[i].axis('off')
        
        plt.tight_layout()
        plt.show()

    # 3/ global bigrams 
    print("Global bigrams : ")
    plot_bigrams(all_tokens, title ="Top 20 bigrammes", top_n=20)

    # 4/ comparative bigrams by site
    fig, axes = plt.subplots(1, n_sites, figsize=(6 * n_sites, 6))

    if n_sites == 1:
        axes = [axes]

    for i, site in enumerate(sites_to_compare):
        site_df = df[df['site_name'].str.lower() == site.lower()]
        site_tokens = []

        for q in site_df['question']:
            site_tokens.extend(extract_tokens(q))

        plot_bigrams(site_tokens,title=f"{site} – Top 5 Bigrammes",top_n=5,ax=axes[i])

    plt.tight_layout()
    plt.show()

    # 5/ Global intent view
    print("\nGlobal intent treemap :")
    global_treemap(df)

    # 6/ Comparative intent view
    print(f"\nComparing intent profiles for : {', '.join(sites_to_compare)}")
    comparative_treemaps(df, sites_to_compare)

    # 7/ compare questions lenght by site  
    df['question_len'] = df['question'].apply(lambda x: len(x.split()))
    sns.boxplot(x='site_name', y='question_len', data=df)
    plt.xlabel("Nom du site", fontsize=12)
    plt.ylabel("Nombre de mots par question", fontsize=12)
    plt.title("Distribution de la longueur des questions par site")
    plt.show()

     # 8/ cooccurrence heatmap
    docs_for_matrix = {i: extract_tokens(q) for i, q in enumerate(df['question'])}
    print("Generating co-occurrence matrix : ")
    plot_cooccurrence_matrix(docs_for_matrix, top_n=15)