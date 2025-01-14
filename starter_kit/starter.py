import os
import glob
import json
import random
import networkx as nx
import test_solution
import datetime
import matplotlib.pyplot as plt
import seaborn as sns

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

def solve(dataset_txt, depth_complexity):
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
            def evaluate_path(G, path, curr_battery, visited_roads, dist_to_base, dataset, depth):
                """Évalue un chemin possible en fonction de plusieurs critères"""
                total_score = 0
                remaining_battery = curr_battery
                current_visited = visited_roads.copy()

                # Évaluer chaque étape du chemin
                for i in range(len(path)-1):
                    node1, node2 = path[i], path[i+1]
                    edge_len = G[node1][node2]['length']

                    if remaining_battery < edge_len:
                        return float('-inf')  # Chemin impossible

                    remaining_battery -= edge_len

                    # Bonus pour routes non visitées
                    if (node1, node2) not in current_visited:
                        total_score += 100 * (1 / (depth + 1))  # Diminue avec la profondeur
                        current_visited.add((node1, node2))

                    # Bonus pour la longueur de la route
                    total_score += edge_len / 10

                    # Bonus pour les voisins non visités du prochain nœud
                    unvisited_neighbors = sum(1 for neighbor in G.neighbors(node2)
                                            if (node2, neighbor) not in current_visited)
                    total_score += unvisited_neighbors * 5 * (1 / (depth + 1))

                    # Pénalité si on ne peut pas rentrer à la base
                    if remaining_battery < dist_to_base[node2]:
                        total_score -= 1000

                    # Pénalité pour retour non nécessaire à la base
                    if node2 == base_id and remaining_battery > dataset['batteryCapacity'] / 10:
                        total_score -= 500

                return total_score

            def find_best_path(G, curr_node, battery_remaining, visited_roads, dist_to_base, dataset, depth=0, max_depth=3):
                """Trouve le meilleur chemin à partir du nœud actuel avec une profondeur donnée"""
                if depth >= max_depth:
                    return [], 0

                best_path = []
                best_score = float('-inf')

                neighbors = list(G.neighbors(curr_node))
                for next_node in neighbors:
                    edge_len = G[curr_node][next_node]['length']

                    # Vérifier si le mouvement est possible
                    if battery_remaining >= edge_len:
                        # Évaluer le chemin direct
                        path = [curr_node, next_node]
                        score = evaluate_path(G, path, battery_remaining, visited_roads, dist_to_base, dataset, depth)

                        # Explorer récursivement
                        if depth < max_depth - 1:
                            next_battery = battery_remaining - edge_len
                            next_visited = visited_roads.copy()
                            if (curr_node, next_node) not in next_visited:
                                next_visited.add((curr_node, next_node))

                            sub_path, sub_score = find_best_path(G, next_node, next_battery, next_visited,
                                                            dist_to_base, dataset, depth + 1, max_depth)

                            if sub_path:
                                path.extend(sub_path[1:])
                                score += sub_score * (0.8 ** depth)  # Diminution de l'importance avec la profondeur

                        if score > best_score:
                            best_score = score
                            best_path = path

                return best_path, best_score

            best_path, _ = find_best_path(G, curr_node, battery_remaining, visited_roads, dist_to_base, dataset, depth=0, max_depth=depth_complexity)

            if best_path and len(best_path) > 1:
                next_node = best_path[1]
            else:
                # Logique de secours si aucun bon chemin n'est trouvé
                next_node = base_id

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

def save_score_history(dataset_file, depth_number, score, is_valid, roads_length, timestamp=None):
    """Sauvegarde l'historique des scores dans un fichier JSON"""
    cache_dir = f'cache/scores/{dataset_file}'
    os.makedirs(cache_dir, exist_ok=True)

    history_file = f'{cache_dir}/history_depth_{depth_number}.json'

    # Charger l'historique existant ou créer un nouveau
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {
            'dataset': dataset_file,
            'depth_number': depth_number,
            'roads_length': roads_length,
            'scores': [],
            'stats': {
                'highest_score': 0,
                'lowest_score': float('inf'),
                'valid_attempts': 0,
                'invalid_attempts': 0,
                'total_attempts': 0
            }
        }

    # Mettre à jour les statistiques
    if timestamp is None:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    score_entry = {
        'score': score,
        'is_valid': is_valid,
        'timestamp': timestamp
    }

    # Limiter le nombre d'entrées en fonction de la taille du dataset
    max_entries = min(1000, max(100, int(roads_length / depth_number)))
    history['scores'].append(score_entry)
    if len(history['scores']) > max_entries:
        history['scores'] = history['scores'][-max_entries:]

    # Mettre à jour les stats
    stats = history['stats']
    stats['total_attempts'] += 1
    if is_valid:
        stats['valid_attempts'] += 1
        stats['highest_score'] = max(stats['highest_score'], score)
        stats['lowest_score'] = min(stats['lowest_score'], score)
    else:
        stats['invalid_attempts'] += 1

    # Sauvegarder l'historique
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)

    return history

def loop():
    # Charger le dataset et obtenir le nombre de routes
    dataset_data = json.loads(dataset)
    roads_length = len(dataset_data['roads'])
    print(f"Dataset {dataset_file} contains {roads_length} roads")

    highest_existing_score = get_highest_score_from_files(dataset_file)
    best_result = None
    best_score = 0

    for attempt in range(max_attempts):
        print(f"\nAttempt {attempt + 1}/{max_attempts}")
        solution = solve(dataset, depth_number)
        score, is_valid, message = test_solution.getSolutionScore(solution, dataset)

        # Sauvegarder dans l'historique
        history = save_score_history(dataset_file, depth_number, score, is_valid, roads_length)

        if is_valid and score > best_score:
            best_score = score
            best_result = solution

            if score > highest_existing_score:
                print(f'✅ New best score! (Previous best: {highest_existing_score})')

                # Supprimer les anciennes solutions
                pattern = f'.\\solutions\\{dataset_file}_*.json'
                for old_file in glob.glob(pattern):
                    try:
                        old_score = int(old_file.split('_')[2])
                        if old_score < score:
                            os.remove(old_file)
                    except (IndexError, ValueError):
                        continue

                # Sauvegarder la nouvelle solution
                date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                file_name = f'{dataset_file}_{score}_{date}'

                with open(f'.\\solutions\\{file_name}.json', 'w') as f:
                    f.write(best_result)
                print(f'💾 Solution saved: {file_name}')

        elif not is_valid:
            print(f'❌ Invalid solution: {message}')

        # Afficher les stats périodiquement
        if (attempt + 1) % 10 == 0:
            stats = history['stats']
            print(f"\n📊 Current Statistics (Depth {depth_number}):")
            print(f"Highest Score: {stats['highest_score']}")
            print(f"Lowest Valid Score: {stats['lowest_score']}")
            print(f"Valid/Total Attempts: {stats['valid_attempts']}/{stats['total_attempts']}")

    print(f'\n🏁 Final best score: {best_score}')
    return best_score

def analyze_history(dataset_file=None, depth_number=None):
    """Analyse l'historique des scores et génère des visualisations"""

    cache_dir = 'cache/scores'
    if dataset_file and depth_number:
        files = [f'{cache_dir}/{dataset_file}/history_depth_{depth_number}.json']
    else:
        files = glob.glob(f'{cache_dir}/**/history_depth_*.json', recursive=True)

    plt.figure(figsize=(15, 10))

    for file in files:
        with open(file, 'r') as f:
            history = json.load(f)

        valid_scores = [entry['score'] for entry in history['scores'] if entry['is_valid']]

        sns.kdeplot(valid_scores, label=f"{history['dataset']} (Depth {history['depth_number']})")

    plt.title('Score Distribution by Dataset and Depth')
    plt.xlabel('Score')
    plt.ylabel('Density')
    plt.legend()

    # Sauvegarder le graphique
    os.makedirs('cache/visualizations', exist_ok=True)
    plt.savefig('cache/visualizations/score_distribution.png')
    print('📈 Generated visualization: cache/visualizations/score_distribution.png')
    # Vérifie si la meilleure solution trouvée est meilleure que les solutions existantes
    highest_existing_score = get_highest_score_from_files(dataset_file)

    best_result = None
    lowest_score = highest_existing_score
    best_score = 0

    for attempt in range(max_attempts):
        solution = solve(dataset, depth_number)
        score, is_valid, message = test_solution.getSolutionScore(solution, dataset)

        if is_valid and score < lowest_score:
            lowest_score = score

        if is_valid and score > best_score:
            best_score = score
            best_result = solution

        if is_valid and score > highest_existing_score:
            highest_existing_score = score
            print(f'✅ New best score! {best_score} (Previous best: {highest_existing_score})')

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
        
    print(f'Best score found: {best_score}')

# dataset_file = "1_example"
# dataset_file = "2_pacman"
dataset_file = "3_efrei"
# dataset_file = "4_manhattan"
# dataset_file = "5_gta"
# dataset_file = "6_paris"
# dataset_file = "7_london"
dataset = open(f'.\\datasets\\{dataset_file}.json').read()
depth_number = 3
max_attempts = 100
print('---------------------------------')
print(f'Solving {dataset_file}')
# loop()

# Analyser un dataset spécifique
# analyze_history("1_example", 7)

# Analyser tous les datasets
# analyze_history()