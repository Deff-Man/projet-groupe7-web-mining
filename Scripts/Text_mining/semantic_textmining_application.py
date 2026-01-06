import os
import numpy as np
import pandas as pd
 
from sklearn.decomposition import NMF
from sklearn.preprocessing import normalize
 
from gensim.corpora import Dictionary
from gensim.models.coherencemodel import CoherenceModel
 
def nmf_topics_from_tfidf(
    csv_path: str,
    output_dir: str,
    k_values=(3,5,7,9,11,13,15),
    topn_words: int = 15,
    random_state: int = 42):
    # create output directory if it does not exist
    os.makedirs(output_dir, exist_ok=True)
 
    # load tf-idf matrix
    X = pd.read_excel(r"C:\Users\User\Desktop\Master 1\Web mining\2_matrix_tfidf_global.xlsx")
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0.0)
 
    # check non-negativity constraint required by nmf
    if (X.values < 0).any():
        raise ValueError("Negative values detected.")
 
    # remove empty columns
    X = X.loc[:, X.sum(axis=0) > 0]
 
    # remove empty documents
    X = X.loc[X.sum(axis=1) > 0].copy()
 
    print(f"Docs: {X.shape[0]}")
    print(f"Terms: {X.shape[1]}")
 
    tokens = list(X.columns)
 
    # prepare gensim structures for coherence computation
    X_np = X.to_numpy()
    texts = [list(np.asarray(tokens)[row > 0]) for row in X_np]
 
    # build dictionary from full vocabulary
    id2word = Dictionary([tokens])
 
    # grid search over k values using coherence c_v
    scores = []
    models = {}
 
    for k in k_values:
        # initialize nmf model
        nmf = NMF(n_components=k,init="nndsvda",random_state=random_state,max_iter=1000)
 
        # fit nmf
        W = nmf.fit_transform(X_np)
        H = nmf.components_
 
        # normalize document-topic matrix for interpretation
        Wn = normalize(W, norm="l1", axis=1)
 
        # extract top words per topic
        topic_words = []
        for topic_id in range(k):
            top_idx = np.argsort(H[topic_id])[::-1][:topn_words]
            topic_words.append([tokens[i] for i in top_idx])
 
        # compute coherence c_v
        cm = CoherenceModel(
            topics=topic_words,
            texts=texts,
            dictionary=id2word,
            coherence="c_v",
            processes=1,)
        coh = cm.get_coherence()
 
        scores.append({"k": k, "coherence_cv": coh})
        models[k] = (nmf, Wn, H)
 
        print(f"K={k:>2} | coherence(c_v)={coh:.4f}")
 
    # select best k based on coherence
    scores_df = pd.DataFrame(scores).sort_values("coherence_cv", ascending=False)
    scores_df.to_csv(os.path.join(output_dir, "k_coherence_scores_nmf.csv"), index=False)
 
    best_k = int(scores_df.iloc[0]["k"])
    nmf_best, Wn_best, H_best = models[best_k]
 
    print(f"\nBest k = {best_k} (coherence c_v = {scores_df.iloc[0]['coherence_cv']:.4f})")
 
    # export topic-word distributions
    topics_rows = []
    for topic_id in range(best_k):
        top_idx = np.argsort(H_best[topic_id])[::-1][:topn_words]
        for rank, j in enumerate(top_idx, start=1):
            topics_rows.append({
                "topic": topic_id,
                "rank": rank,
                "word": tokens[j],
                "weight": float(H_best[topic_id, j]),})
 
    pd.DataFrame(topics_rows).to_csv(os.path.join(output_dir, f"topics_nmf_k{best_k}.csv"),index=False)
    doc_topics_df = pd.DataFrame(Wn_best,columns=[f"topic_{i}" for i in range(best_k)])

    doc_topics_df.to_csv(os.path.join(output_dir, f"doc_topics_nmf_k{best_k}.csv"),index=True,index_label="doc_id")
    
    # count dominant topic per document
    doc_topics_path = os.path.join(output_dir, f"doc_topics_nmf_k{best_k}.csv")

    # reload doc-topic probabilities
    df_topics = pd.read_csv(doc_topics_path)

    # topic columns
    topic_cols = [c for c in df_topics.columns if c.startswith("topic_")]
    if len(topic_cols) == 0:
        raise ValueError("No topic_* columns found in doc_topics file.")

    # dominant topic per document
    df_topics["dominant_topic"] = df_topics[topic_cols].idxmax(axis=1)

    # counts + percentages
    counts = df_topics["dominant_topic"].value_counts().sort_index()
    percents = (counts / counts.sum() * 100).round(2)

    # final table
    summary_df = pd.DataFrame({
        "dominant_topic": counts.index,
        "n_docs": counts.values,
        "pct_docs": percents.values})

    # export
    summary_path = os.path.join(output_dir, f"dominant_topic_counts_nmf_k{best_k}.csv")
    summary_df.to_csv(summary_path, index=False)

    print(f"dominant_topic_counts_nmf_k{best_k}.csv")
    print("Output written to:", output_dir)
    print(f"topics_nmf_k{best_k}.csv")
    print(f"doc_topics_nmf_k{best_k}.csv")
 
if __name__ == "__main__":
    # define input and output paths
    CSV_TFIDF_PATH = r"C:\Users\User\Desktop\Master 1\Web mining\2_matrix_tfidf_global.xlsx"
    OUTPUT_DIR = r"C:\Users\User\Desktop\Master 1\Web mining\NMF_Results"
 
    nmf_topics_from_tfidf(csv_path=CSV_TFIDF_PATH,output_dir=OUTPUT_DIR,k_values=(3,5,7,9,11,13,15),topn_words=10,random_state=42)