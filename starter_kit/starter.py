import os
import glob
import json
import random
import networkx as nx
import test_solution
import datetime

def analyze_base_nodes(G, dataset):
    """Analyse tous les noeuds et retourne les 10% meilleurs avec leurs caractéristiques"""
    nodes_analysis = {}

    def count_neighbors_at_depth(G, start_node, max_depth, battery_limit):
        """Compte les voisins accessibles à chaque profondeur avec contrainte de batterie"""
        visited = set([start_node])
        depth_counts = {d: 0 for d in range(1, max_depth + 1)}
        queue = [(start_node, 0, battery_limit)]  # (node, depth, remaining_battery)

        while queue:
            current, depth, battery = queue.pop(0)
            if depth >= max_depth:
                continue

            for neighbor in G.neighbors(current):
                edge_length = G[current][neighbor]['length']
                if neighbor not in visited and edge_length <= battery:
                    visited.add(neighbor)
                    depth_counts[depth + 1] += 1
                    new_battery = battery - edge_length
                    queue.append((neighbor, depth + 1, new_battery))

        return depth_counts

    for node in G.nodes():
        score = 0

        # Critère 1 : Nombre de voisins directs et jusqu'à profondeur 5
        depth_neighbors = count_neighbors_at_depth(G, node, 5, dataset['batteryCapacity'])
        num_neighbors = depth_neighbors[1]  # Voisins directs
        score += num_neighbors * 10
        all_num_neighbors = 0

        # Bonus pour les voisins à différentes profondeurs (décroissant avec la profondeur)
        for depth, count in depth_neighbors.items():
            all_num_neighbors += count
            score += count * (10 / depth)  # Plus la profondeur augmente, moins le bonus est important

        # Critère 2 : Centralité du nœud
        try:
            paths = nx.single_source_dijkstra_path_length(G, node, weight='length')
            avg_distance = sum(paths.values()) / len(paths)
            centrality_score = (dataset['batteryCapacity'] / (avg_distance + 1)) * 20
            score += centrality_score
        except:
            continue

        # Critère 3 : Routes accessibles
        reachable_edges = 0
        visited = set()

        def count_reachable_edges(current, remaining_battery, visited):
            nonlocal reachable_edges
            for neighbor in G.neighbors(current):
                edge = (min(current, neighbor), max(current, neighbor))
                if edge not in visited and G[current][neighbor]['length'] <= remaining_battery:
                    visited.add(edge)
                    reachable_edges += 1
                    new_battery = remaining_battery - G[current][neighbor]['length']
                    if new_battery > 0:
                        count_reachable_edges(neighbor, new_battery, visited)

        count_reachable_edges(node, dataset['batteryCapacity'], visited)
        score += reachable_edges * 15

        # Critère 4 : Routes à sens unique
        outgoing_one_way = sum(1 for neighbor in G.neighbors(node)
                              if G[node][neighbor].get('one_way', False))
        score += outgoing_one_way * 5

        # Critère 5 : Longueur des routes connectées
        total_connected_length = sum(G[node][neighbor]['length']
                                   for neighbor in G.neighbors(node))
        score += total_connected_length / 10

        # Sauvegarder les caractéristiques
        nodes_analysis[node] = {
            'score': score,
            'num_neighbors': num_neighbors,
            'all_num_neighbors': all_num_neighbors,
            'neighbors_by_depth': depth_neighbors,
            'avg_distance': avg_distance,
            'reachable_edges': reachable_edges,
            'outgoing_one_way': outgoing_one_way,
            'total_connected_length': total_connected_length
        }

    # Trier les noeuds par score
    sorted_nodes = sorted(nodes_analysis.items(), key=lambda x: x[1]['score'], reverse=True)

    # Prendre les 10% meilleurs avec minimum 5 noeuds
    num_top_nodes = max(5, int(len(sorted_nodes) * 0.1))
    top_nodes = sorted_nodes[:num_top_nodes]

    return top_nodes

def get_cached_base_nodes(dataset_file):
    """Récupère les noeuds de base depuis le cache ou les calcule si nécessaire"""
    cache_dir = 'cache/base_nodes'
    cache_file = f'{cache_dir}/base_nodes_cache_{dataset_file}.json'

    # Créer le dossier de cache s'il n'existe pas
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create cache directory: {e}")
        return None

    try:
        # Essayer de lire le cache
        with open(cache_file, 'r') as f:
            return json.load(f)
    except (PermissionError, FileNotFoundError) as e:
        print(f"Warning: Could not access cache file: {e}")
        return None
    except Exception as e:
        print(f"Warning: Unexpected error while reading cache: {e}")
        return None

def save_cached_base_nodes(dataset_file, nodes):
    """Sauvegarde les noeuds de base dans le cache"""
    cache_dir = 'cache/base_nodes'
    cache_file = f'{cache_dir}/base_nodes_cache_{dataset_file}.json'

    try:
        # Créer le dossier de cache s'il n'existe pas
        os.makedirs(cache_dir, exist_ok=True)

        # Sauvegarder dans le cache
        with open(cache_file, 'w') as f:
            json.dump(nodes, f)
    except Exception as e:
        print(f"Warning: Could not save to cache: {e}")

def find_best_base(G, dataset, dataset_file):
    """Trouve le meilleur noeud de base"""
    # Essayer de récupérer depuis le cache
    cached_nodes = get_cached_base_nodes(dataset_file)

    if cached_nodes is None:
        # Si le cache n'est pas accessible, calculer les noeuds
        cached_nodes = analyze_base_nodes(G, dataset)
        # Essayer de sauvegarder dans le cache
        save_cached_base_nodes(dataset_file, cached_nodes)

    # Retourner un noeud au hasard parmi les meilleurs
    random_node = random.choice(cached_nodes)
    print(f"\nChosen base node {random_node[0]} with score {random_node[1]['score']:.2f}")
    return int(random_node[0])

def solve(dataset_txt):
    # Lecture du dataset
    dataset = json.loads(dataset_txt)

    # On crée le graphe du réseau avec networkx. On aurait pu le faire aussi avec un simple dictionnaire Python
    # networkx permet cependant d'avoir accès à certaines fonctions comme le calcul des distances plutôt que de les recoder
    G = nx.DiGraph()
    for edge in dataset['roads']:
        if edge['isOneWay']:
            G.add_edge(edge['intersectionId1'], edge['intersectionId2'], length=edge['length'], one_way=True)
        else:
            G.add_edge(edge['intersectionId1'], edge['intersectionId2'], length=edge['length'], one_way=False)
            G.add_edge(edge['intersectionId2'], edge['intersectionId1'], length=edge['length'], one_way=False)

    # Choix de la station de charge : on prend l'intersection 0 par défaut. Il y a peut-être mieux à faire !
    base_id = find_best_base(G, dataset, dataset_file)

    # Crée un dictionnaire des distances de chaque noeud à la base
    dist_to_base = nx.shortest_path_length(G, source=None, target=base_id, weight='length')    

    visited_roads = set()  # Ensemble des routes visitées
    curr_node = base_id  # Noeud courant, initialisé à la base
    path = [base_id]  # Chemin parcouru, initialisé avec la base
    score = 0  # Score initialisé à 0

    # Boucle sur chaque jour
    for day_i in range(dataset['numDays']):
        battery_remaining = dataset['batteryCapacity']  # Réinitialisation de la batterie au maximum

        # Boucle principale pour parcourir les routes
        while True:
            # On mélange les voisins pour éviter de toujours prendre le même chemin
            neighbors = list(G.neighbors(curr_node))
            random.shuffle(neighbors)
            
            
            # L'agorithme du choix du prochain noeud est là !
            # Commencez par trouver un meilleur algorithme que celui-ci
            # -------------------------------------------
            # Stratégie améliorée pour choisir le prochain nœud
            next_node = None
            best_priority = -1
            has_alternative = False  # Pour tracker si on a d'autres options viables

            # Pour chaque voisin possible
            for nxt in neighbors:
                edge_len = G[curr_node][nxt]['length']  # Longueur de la route vers ce voisin

                # Vérification différente selon si c'est le dernier jour ou non
                can_move = False
                if day_i == dataset['numDays'] - 1:
                    if nxt == base_id:
                        can_move = battery_remaining >= edge_len
                    else:
                        distance_to_base = dist_to_base[nxt]
                        can_move = battery_remaining >= (edge_len + distance_to_base)
                else:
                    can_move = battery_remaining >= edge_len + dist_to_base[nxt]

                # Si le mouvement est possible
                if can_move:
                    # Initialisation du score de priorité pour ce nœud
                    priority = 0

                    # Priorité 1: Routes non visitées (bonus important)
                    if (curr_node, nxt) not in visited_roads:
                        priority += 100

                    # Priorité 2: Bonus pour les routes plus longues
                    priority += edge_len / 10

                    # Priorité 3: Bonus pour les nœuds ayant beaucoup de voisins non visités
                    unvisited_neighbors = sum(1 for neighbor in G.neighbors(nxt)
                                            if (nxt, neighbor) not in visited_roads)
                    priority += unvisited_neighbors * 5

                    # Priorité 4: Gestion de la batterie et retour à la base
                    battery_after_move = battery_remaining - edge_len
                    if battery_after_move < dist_to_base[nxt]:
                        priority -= 1000  # Forte pénalité si on risque de ne pas pouvoir rentrer

                    # Priorité 5: Pénalité pour retour à la base si non nécessaire
                    if nxt == base_id:
                        # Vérifier s'il existe d'autres chemins viables
                        remaining_battery_if_skip_base = battery_remaining - edge_len
                        if remaining_battery_if_skip_base > dataset['batteryCapacity'] / 3:
                            priority -= 500  # Forte pénalité pour retour non nécessaire à la base

                    # Priorité 6: Gestion différente selon le jour
                    if day_i == dataset['numDays'] - 1:
                        if (curr_node, nxt) not in visited_roads:
                            priority += 50
                    else:
                        if dist_to_base[nxt] < dataset['batteryCapacity'] / 3:
                            priority += 10

                    # Mise à jour du meilleur nœud si la priorité est plus élevée
                    if priority > best_priority:
                        best_priority = priority
                        next_node = nxt

                    # Marquer qu'on a une alternative viable si ce n'est pas la base
                    if nxt != base_id and battery_after_move >= dist_to_base[nxt]:
                        has_alternative = True

            # Si on a choisi la base mais qu'il existe des alternatives viables
            if next_node == base_id and has_alternative and battery_remaining > dataset['batteryCapacity'] / 3:
                # Rechercher à nouveau le meilleur nœud en excluant la base
                best_priority = -1
                for nxt in [n for n in neighbors if n != base_id]:
                    # [Répéter la logique de priorité précédente en excluant la base]
                    # ... [même code que ci-dessus sans la partie base_id]
                    if can_move and nxt != base_id:
                        # [Calcul de priorité comme avant]
                        if priority > best_priority:
                            best_priority = priority
                            next_node = nxt

            # Vérifications de sécurité finales
            if next_node is None or (next_node != base_id and
                battery_remaining - G[curr_node][next_node]['length'] < dist_to_base[next_node]):
                try:
                    path_to_base = nx.shortest_path(G, curr_node, base_id, weight='length')
                    total_distance = sum(G[path_to_base[i]][path_to_base[i+1]]['length']
                                    for i in range(len(path_to_base)-1))
                    if len(path_to_base) > 1 and total_distance <= battery_remaining:
                        next_node = path_to_base[1]
                    else:
                        next_node = base_id
                except nx.NetworkXNoPath:
                    next_node = base_id
            # -------------------------------------------

            # Mise à jour du score si la route n'a pas été visitée
            if (curr_node, next_node) not in visited_roads:
                score += G[curr_node][next_node]['length']

            # Ajout des routes visitées dans les deux sens
            visited_roads.add((curr_node, next_node))
            visited_roads.add((next_node, curr_node))

            # Mise à jour de la batterie restante
            battery_remaining -= G[curr_node][next_node]['length']

            # Ajout du prochain noeud au chemin
            path.append(next_node)
            curr_node = next_node

            # On termine la journée si on est de retour à la base
            if curr_node == base_id:
                break

        print(f'End day {day_i+1} with {battery_remaining} battery')  # Message de fin de jour


    # Message de fin de routage
    print(f'Visited {len(visited_roads) // 2} / {len(dataset["roads"])} roads')
    print(f'Expected score: {score:_}')

    # Retour du résultat sous forme de chaîne JSON
    return json.dumps({"chargeStationId": base_id, "itinerary": path})

def get_highest_score_from_files(dataset_file):
    # Cherche tous les fichiers de solution pour ce dataset
    pattern = f'.\\solutions\\{dataset_file}_*.json'
    files = glob.glob(pattern)

    highest_score = 0
    for file in files:
        # Extrait le score du nom du fichier
        try:
            # Le nom du fichier est de la forme "dataset_score_date.json"
            score = int(file.split('_')[2])
            highest_score = max(highest_score, score)
        except (IndexError, ValueError):
            continue

    return highest_score

def loop():
    max_attempts = 1000
    best_result = None
    best_score = 0

    # Vérifie si la meilleure solution trouvée est meilleure que les solutions existantes
    highest_existing_score = get_highest_score_from_files(dataset_file)

    for attempt in range(max_attempts):
        solution = solve(dataset)
        score, is_valid, message = test_solution.getSolutionScore(solution, dataset)

        if is_valid and score > best_score:
            best_score = score
            best_result = solution

        if is_valid and score > highest_existing_score:
            print(f'✅ New best score! (Previous best: {highest_existing_score})')

            # Supprimer les anciennes solutions avec des scores inférieurs
            pattern = f'.\\solutions\\{dataset_file}_*.json'
            for old_file in glob.glob(pattern):
                try:
                    old_score = int(old_file.split('_')[2])
                    if old_score < score:
                        os.remove(old_file)
                except (IndexError, ValueError):
                    continue

            # Sauvegarder la nouvelle meilleure solution
            date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f'{dataset_file}_{score}_{date}'

            with open(f'.\\solutions\\{file_name}.json', 'w') as f:
                f.write(best_result)
            # print('Best solution saved')
        elif not is_valid:
            print(f'❌ Invalid solution: {message}')
        
    print

dataset_file = "1_example"
# dataset_file = "2_pacman"
# dataset_file = "3_efrei"
# dataset_file = "4_manhattan"
# dataset_file = "5_gta"
# dataset_file = "6_paris"
# dataset_file = "7_london"
dataset = open(f'.\\datasets\\{dataset_file}.json').read()

print('---------------------------------')
print(f'Solving {dataset_file}')
loop()