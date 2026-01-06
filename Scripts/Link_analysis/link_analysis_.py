import pandas as pd
import networkx as nx
import numpy as np
import os 
from scipy.sparse.csgraph import shortest_path
from collections import Counter


# A/ basic graph matrices
# degree matrix
def degree_matrix(A: np.ndarray, direction: str = "out") -> np.ndarray :
    if direction == "out": 
        deg = A.sum(axis=1)
    elif direction == "in": 
        deg = A.sum(axis=0)
    return np.diag(deg)

# transition_matrix
def transition_matrix(A: np.ndarray, direction: str = "out") -> np.ndarray :
    D = degree_matrix(A, direction)
    deg=np.diag(D)
    P=np.zeros_like(A, dtype=float) 
    for i, d in enumerate(deg):
        if d>0:
            P[i,:]= A[i,:]/d
    return P

# laplacian_matrix
def laplacian_matrix(A: np.ndarray) -> np.ndarray:   
    D = degree_matrix(A)
    L = D-A
    return L

# laplacian_pseudoinverse
def laplacian_pseudoinverse(A: np.ndarray) -> np.ndarray:   
    L = laplacian_matrix(A)
    n=A.shape[0]
    e=np.ones((n,1))
    E= (e @ e.T)/n
    M=L-E
    M_inv =np.linalg.inv(M)
    
    L_pinv = M_inv + E
    return L_pinv

# B/ distance & path measures
# shortest_path
def shortest_path_matrix(B: np.ndarray) -> np.ndarray:
    # work on a copy so we don't modify A
    SP = B.copy().astype(float)
    n = SP.shape[0]

    # preprocess step: replace 0 by "infinity" except on the diagonal
    for i in range(n):
        for j in range(n):
            if i != j and SP[i, j] == 0:
                SP[i, j] = 100000.0

    # Floyd–Warshall
    for k in range(n):
        for i in range(n):
            for j in range(n):
                SP[i, j] = min(SP[i, j], SP[i, k] + SP[k, j])

    # distance from a node to itself is 0
    for i in range(n):
        SP[i, i] = 0.0

    return SP


# C/ centrality measures
# page Rank
def pagerank_power_iteration(A: np.ndarray, alpha: float = 0.85, max_iter: int = 100) -> np.ndarray:
    n = A.shape[0]
    P = transition_matrix(A) # Use the function defined above
    #represents the random jump
    E = np.ones((n, n)) / n
    #initial uniform distribution
    pr = np.ones((n, 1)) / n
   
    # Google Matrix
    G = alpha * P + (1 - alpha) * E
    for _ in range(max_iter):
        # Multiplication : v_new = G.T * v_old
        pr = G.T @ pr
        # Standardization
        pr = pr / pr.sum()
    #return Final PageRank vector (importance of each node)
    return pr.flatten()

# eccentricity and radius
def eccentricity_centrality(B: np.ndarray) -> np.ndarray:
    SP = shortest_path_matrix(B) 
    n = SP.shape[0]
    ecc = np.zeros(n, dtype=float)
    for i in range(n):
        dists = SP[i, :]
        valid_dists = dists[dists < 90000.0]
        if len(valid_dists) > 0:
            ecc[i] = valid_dists.max() 
        else :
            ecc[i] = 100000.0 

    with np.errstate(divide='ignore'):
        res = 1 / ecc 
    return res


# closeness
def closeness_centrality(B: np.ndarray) -> np.ndarray:
    SP = shortest_path_matrix(B)   
    n = SP.shape[0]
    closeness = np.zeros(n)
    
    for i in range(n):
        dist_sum = np.sum(SP[i, :])
        if dist_sum > 0:
            closeness[i] = (n - 1) / dist_sum
        else:
            closeness[i] = 0
    return closeness

# betweenness
def calcul_betweenness(B: np.ndarray) -> dict:
    G = nx.from_numpy_array(B)
    centrality_scores = nx.betweenness_centrality(G, normalized=False)
    return centrality_scores


# degree centrality 
def degree_centrality (df : pd.DataFrame) -> pd.DataFrame :
    # safety: ensure all values are numeric
    df_numeric = df.apply(pd.to_numeric, errors="coerce").fillna(0)
    # Centrality of degree (binary):
    # count the number of 1s on each row
    degree_centrality = (df_numeric == 1).sum(axis=1)
    # clean result
    degree_df = (degree_centrality.reset_index().rename(columns={"index": "token", 0: "degree_centrality"}).sort_values(by="degree_centrality", ascending=False))
    return degree_df


# stationnary distribution
def get_stationary_distribution(A: np.ndarray) -> np.ndarray:
    P = transition_matrix(A, direction="out")
    eigenvalues, eigenvectors = np.linalg.eig(P.T)
    idx = np.argmin(np.abs(eigenvalues - 1))
    v = np.real(eigenvectors[:, idx])
    return v / v.sum()

# D/ similarity measures 
# common neighbors 
def common_neighbors_matrix(B: np.ndarray) -> np.ndarray:
    CN = B @ B.T
    return CN

# preferential attachment
def preferential_attachment_matrix(B: np.ndarray) -> np.ndarray:
    d_out = np.diag(degree_matrix(B, "out")) 
    d_in = np.diag(degree_matrix(B, "in"))
    PA = np.zeros_like(B,dtype=float)
    n = B.shape[0]
    for i in range(n):
        for j in range(n): 
            PA[i,j]= d_in[i]*d_out[j]
    return PA

# jaccard similairty
def jaccard_similarity_matrix(B: np.ndarray) -> np.ndarray:
    Numérateur = common_neighbors_matrix(B)
    d_out = np.diag(degree_matrix(B, "out")) 
    d_in = np.diag(degree_matrix(B, "in"))
    Den1= np.zeros_like(B,dtype=float)
    n = B.shape[0]
    for i in range(n):
        for j in range(n): 
            Den1[i,j]= d_in[i]+d_out[j]
    
    jacard = Numérateur/(Den1-Numérateur)
    return jacard


# E/ analyze subgroups
def analyze_subgroups(B, labels, output_folder):
    G_sub = nx.from_numpy_array(B)
    G_sub.remove_edges_from(nx.selfloop_edges(G_sub))
    n_nodes = G_sub.number_of_nodes()

    # analyze cliques
    distribution = Counter()
    nb_cliques = 0
    max_size = 0
    biggest_cliques = []
    
    for clique in nx.find_cliques(G_sub):
        t = len(clique)
        distribution[t] += 1
        nb_cliques += 1
        if t > max_size:
            max_size = t
            biggest_cliques = [clique]
        elif t == max_size:
            biggest_cliques.append(clique)

    print(f"Total number of maximal cliques: {nb_cliques}")
    print(f"Size of the biggest clique: {max_size}\n")
    
    print("Distribution of cliques by size:")
    # we sort by size descending 
    clique_dist_export = []
    for size in sorted(distribution.keys(), reverse=True):
        count = distribution[size]
        print(f" - Clique of size {size} : {count}")
        clique_dist_export.append({"Size": size, "Count": count})

    # show the Top 3 largest cliques 
    print("\nTop 3 Largest Cliques:")
    sorted_cliques = sorted(biggest_cliques, key=len, reverse=True)
    top_cliques_export = []
    
    for i, clique in enumerate(sorted_cliques[:3], 1):
        clique_labels = [labels[idx] for idx in clique]
        print(f" Clique {i} ({len(clique)} nodes): {clique_labels}")
        top_cliques_export.append({
            "Rank": i, 
            "Size": len(clique), 
            "Concepts": " / ".join(clique_labels)})
    
    # analyze n-cliques
    def find_n_cliques(G, N):
        visited = set()
        components = []
        nodes = list(G.nodes())
        for node in nodes:
            if node in visited:
                continue
            # BFS limited to N steps
            sub_nodes = set(nx.single_source_shortest_path_length(G, node, cutoff=N).keys())
            H = G.subgraph(sub_nodes)
            if nx.is_connected(H) and nx.diameter(H) <= N:
                components.append(sub_nodes)
                visited |= sub_nodes
        return components
    
    for N in [2, 3, 4, 5]:
        comps = find_n_cliques(G_sub, N)
        sizes = sorted([len(c) for c in comps], reverse=True)
        
        print(f" {N}-cliques:")
        if len(comps) == 1 and sizes[0] == n_nodes:
            note = f"The entire graph forms an {N}-clique."
            print(f" - {note} ({n_nodes} nodes)")
        else:
            print(f"Number of {N}-cliques: {len(comps)}")
            print(f"Largest sizes: {sizes[:5]}")
          
    # analyze k-cores
    print("\n K-cores analysis :")
    core_numbers = nx.core_number(G_sub)
    
    for k in range(1, 6):
        # identify nodes belonging to the k-core
        nodes_idx = [node for node, val in core_numbers.items() if val >= k]
        nodes_labels = [labels[idx] for idx in nodes_idx]
        
        print(f"\n {k}-core ({len(nodes_labels)} nodes)")
        if nodes_labels:
            print(", ".join(nodes_labels))
        else:
            print("No nodes found for this core level.")
    

def main():
    # paths 
    path_matrix_weighted = r"C:\Users\User\Desktop\Master 1\Web mining\matrice_adjacence_ponderee.csv"
    path_matrix_binary = r"C:\Users\User\Desktop\Master 1\Web mining\matrice_adjacence_binaire.csv"
    path_nodes_gephi = r"C:\Users\User\Desktop\Master 1\Web mining\nodes_gephi_.csv"
    output_folder = r"C:\Users\User\Desktop\Master 1\Web mining\Results_linkanalysis"
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # load data
    # weighted matrix
    adj_matrix_df = pd.read_csv(path_matrix_weighted, index_col=0)
    A = adj_matrix_df.values
    labels = adj_matrix_df.index.tolist()

    # binary matrix
    adj_bin_df = pd.read_csv(path_matrix_binary, index_col=0)
    B = adj_bin_df.values

    # basic network analysis
    G = nx.from_pandas_adjacency(adj_matrix_df, create_using=nx.Graph)
    print(f"Number of nodes : {G.number_of_nodes()}")
    print(f"Number of edges : {G.number_of_edges()}")
    density = nx.density(G)
    print(f"Graph density : {density:.4f}")
    # identify articulation points 
    articulation_points = list(nx.articulation_points(G))
    print(f"Articulation points identified: {articulation_points}")

    actual_articulation_points = list(nx.articulation_points(G))
    impact_scores = []

    for node in actual_articulation_points:
        G_temp = G.copy()
        G_temp.remove_node(node)
        components = list(nx.connected_components(G_temp))
        num_components = len(components)
        largest_size = max(len(c) for c in components) if components else 0
        impact_scores.append((node, num_components, largest_size))

    # sort and display articulation points by highest number of components first
    impact_scores = sorted(impact_scores, key=lambda x: (x[1], -x[2]), reverse=True)
    print(f"Total number of articulation points : {len(articulation_points)}")
    print("\n Top 3 Critical articulation points :")
    for node, n_comp, l_size in impact_scores[:3]:
        print(f" - {node} : {n_comp} components. Max remaining component size: {l_size})")

    # bridges analysis
    bridges = list(nx.bridges(G))
    print(f"\n Total number of bridges : {len(bridges)}")
    
    # 1/ global centrality measures
    SP = shortest_path_matrix(B)
    pr_scores = pagerank_power_iteration(A)
    cl_scores = closeness_centrality(B)
    stat_probs = get_stationary_distribution(A)
    bet_dict = calcul_betweenness(B)
    radius = eccentricity_centrality(B)

    # 2/ degree centrality
    try:
        df_bin_raw = pd.read_csv(path_matrix_binary, index_col=0)
        degree_df = degree_centrality(df_bin_raw)
        degree_df.to_csv(os.path.join(output_folder, "centralite_degre.csv"), index=False)
    except Exception as e:
        print(f"Error Degree Centrality: {e}")

    print(f"Radius : {radius}")
    
    path_export_complet = os.path.join(output_folder, "Analyze_centrality.xlsx")
    
    with pd.ExcelWriter(path_export_complet) as writer:
        pd.DataFrame({'PageRank': pr_scores}, index=labels).sort_values('PageRank', ascending=False).to_excel(writer, sheet_name='PageRank')
        pd.DataFrame({'Closeness': cl_scores}, index=labels).sort_values('Closeness', ascending=False).to_excel(writer, sheet_name='Closeness')
        bet_scores = [bet_dict.get(i, 0) for i in range(len(labels))]
        pd.DataFrame({'Betweenness': bet_scores}, index=labels).sort_values('Betweenness', ascending=False).to_excel(writer, sheet_name='Betweenness')
        pd.DataFrame(SP, index=labels, columns=labels).to_excel(writer, sheet_name='Matrice_ShortestPath')

    # 3/ cluster analysis
    if not os.path.exists(path_nodes_gephi):
        print ("Gephi node file not found")
        
    nodes_df = pd.read_csv(path_nodes_gephi)
    cluster_col = [c for c in nodes_df.columns if 'modularity' in c.lower()][0]
    node_to_cluster = dict(zip(nodes_df['Label'], nodes_df[cluster_col]))
    
    
    # map centrality scores
    nodes_df['PageRank'] = nodes_df['Label'].map(dict(zip(labels, pr_scores)))
    nodes_df['Closeness'] = nodes_df['Label'].map(dict(zip(labels, cl_scores)))
    nodes_df['Stationary_Prob'] = nodes_df['Label'].map(dict(zip(labels, stat_probs)))
        
    # export clusters summaries
    cluster_summary = []
    stationary_summary = []

    for cid in sorted(nodes_df[cluster_col].unique()):
        c_nodes = nodes_df[nodes_df[cluster_col] == cid]
            
        # Top 5
        top_pr = c_nodes.sort_values(by='PageRank', ascending=False).head(5)['Label'].tolist()
        top_cl = c_nodes.sort_values(by='Closeness', ascending=False).head(5)['Label'].tolist()
            
        cluster_summary.append({'Community': f"Cluster {cid}",'Top PageRank': ", ".join(top_pr),'Top Closeness': ", ".join(top_cl)})
            
        # stationary summary
        stationary_summary.append({'Cluster': cid,'Stationary probability': c_nodes['Stationary_Prob'].sum()})

    # save excel files
    pd.DataFrame(cluster_summary).to_excel(os.path.join(output_folder, "Appendix_Cluster.xlsx"), index=False)
    pd.DataFrame(stationary_summary).sort_values(by='Cluster', ascending=True).to_excel(os.path.join(output_folder, "Appendix_Stationary.xlsx"), index=False)
        
    # 4/ similarity matrix
    matrix_jaccard = jaccard_similarity_matrix(B) 
    matrix_pa = preferential_attachment_matrix(B) 
    matrix_cn = common_neighbors_matrix(B) 

    # inter-clusters and intra-clusters analysis
    sim_list = []
    n = len(labels)
    for i in range(n):
        for j in range(i + 1, n):
            count = int(matrix_cn[i, j])
            if count >1 :
                n1, n2 = labels[i], labels[j]
                c1, c2 = node_to_cluster.get(n1), node_to_cluster.get(n2)
                sim_list.append({'Node1': n1, 'Node2': n2, 
                            'Common_Neighbors': matrix_cn[i, j],
                            'Cluster1': c1, 'Cluster2': c2, 
                            'Same_Cluster': c1 == c2})
    df_sim = pd.DataFrame(sim_list)
        
    # a/ inter-clusters analysis
    inter = df_sim[df_sim['Same_Cluster'] == False]
    annexe_1 = inter.groupby(['Cluster1', 'Cluster2']).agg({'Common_Neighbors': ['min', 'max']}).reset_index()
        
    # we find the top 3 strongest connecting concepts for each cluster pair
    annexe_1['Connected concepts'] = inter.groupby(['Cluster1', 'Cluster2']).apply(
            lambda x: " / ".join((x.nlargest(3, 'Common_Neighbors')['Node1'] + " - " + x.nlargest(3, 'Common_Neighbors')['Node2']).tolist())).values
    annexe_1['Number of common neighbors'] = annexe_1['Common_Neighbors']['min'].astype(str) + " to " + annexe_1['Common_Neighbors']['max'].astype(str)
    annexe_1 = annexe_1[['Cluster1', 'Cluster2', 'Connected concepts', 'Number of common neighbors']]
    annexe_1.columns = ['Source Cluster', 'Target Cluster', 'Connected Concepts', 'Number of Common Neighbors']

    # intra-clusters
    intra = df_sim[df_sim['Same_Cluster'] == True]
    annexe_2 = intra.groupby('Cluster1').agg({'Common_Neighbors': ['min', 'max']}).reset_index()
    annexe_2['Significant Pairs'] = intra.groupby('Cluster1').apply(
            lambda x: " / ".join((x.nlargest(3, 'Common_Neighbors')['Node1'] + " - " + x.nlargest(3, 'Common_Neighbors')['Node2']).tolist())).values
    annexe_2['Number of Common Neighbors'] = annexe_2['Common_Neighbors']['min'].astype(str) + " to " + annexe_2['Common_Neighbors']['max'].astype(str)
    annexe_2 = annexe_2[['Cluster1', 'Significant Pairs', 'Number of Common Neighbors']]
    annexe_2.columns = ['Cluster', 'Significant Pairs', 'Number of Common Neighbors']
    
    # export
    path_7_1 = os.path.join(output_folder, "Appendix_1_connections_inter_clusters.xlsx")
    path_7_2 = os.path.join(output_folder, "Appendix_2_connections_intra_clusters.xlsx")
            
    annexe_1.to_excel(path_7_1, index=False)
    annexe_2.to_excel(path_7_2, index=False)

    # local similarity (Jaccard + PA)
        
    sim_combined_list = []
    n = len(labels)
    for i in range(n):
        for j in range(i + 1, n):
            # filter : at least 3 common neighbors required
            if matrix_cn[i, j] >= 3: 
                n1, n2 = labels[i], labels[j]
                c1, c2 = node_to_cluster.get(n1), node_to_cluster.get(n2)
                    
                sim_combined_list.append({
                        'Concept A': n1, 'Concept B': n2,
                        'Jaccard score': round(matrix_jaccard[i, j], 3),
                        'PA score': int(matrix_pa[i, j]),
                        'Common neighbors': int(matrix_cn[i, j]),
                        'Clusters': f"{c1} - {c2}",
                        'Same cluster': "Yes" if c1 == c2 else "No"})

    df_sim = pd.DataFrame(sim_combined_list)

    # Appendix : Top 5 Jaccard
    top_jaccard = df_sim.sort_values(by='Jaccard score', ascending=False).head(5)
    top_jaccard.to_excel(os.path.join(output_folder, "Appendix_jaccard.xlsx"), index=False)

    # Appendix  : Top 5 PA
    top_pa = df_sim.sort_values(by='PA score', ascending=False).head(5)
    top_pa.to_excel(os.path.join(output_folder, "Appendix_PA.xlsx"), index=False)

    # Analyze subgroups
    analyze_subgroups(B, labels, output_folder)


    print(f"All files successfully generated in: {output_folder}")
if __name__ == "__main__":
    main()