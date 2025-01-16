import os
import json
import random
import networkx as nx
import math

class NodeAnalyser:
    def analyze_base_nodes(G, dataset, dataset_file):
        """Analyse tous les noeuds et met à jour le classement périodiquement"""
        nodes_analysis = {}
        total_nodes = len(G.nodes())
        nodes_processed = 0
        update_frequency = 100  # Mise à jour tous les 100 nœuds
        cache_dir = "cache/base_nodes"
        os.makedirs(cache_dir, exist_ok=True)

        # Construction du nom du fichier
        ranking_file = f"{cache_dir}/base_nodes_cache_{dataset_file}.json"

        def update_ranking_file(new_nodes):
            """Met à jour le fichier de classement"""
            try:
                # Charger le classement existant
                if os.path.exists(ranking_file):
                    with open(ranking_file, 'r') as f:
                        current_ranking = json.load(f)
                        # Convertir l'ancien format si nécessaire
                        if current_ranking and isinstance(current_ranking[0], dict):
                            current_ranking = [[entry['node_id'], entry['stats']] for entry in current_ranking]
                else:
                    current_ranking = []

                # Convertir les nouveaux nœuds au format souhaité
                new_entries = [
                    [node, data]  # Format direct [node_id, stats]
                    for node, data in new_nodes
                ]

                # Combiner ancien et nouveau classement
                all_entries = current_ranking + new_entries

                # Trier par score
                all_entries.sort(key=lambda x: x[1]['score'], reverse=True)

                # Garder les 20 meilleurs
                top_entries = all_entries[:20]

                # Sauvegarder le nouveau classement
                with open(ranking_file, 'w') as f:
                    json.dump(top_entries, f, indent=2)

                print(f"📊 Classement mis à jour dans {ranking_file}")
                print(f"   Top score: {top_entries[0][1]['score']:.2f}")
            except Exception as e:
                print(f"❌ Erreur lors de la mise à jour du classement: {e}")

        # [Le reste des fonctions helpers reste identique]
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

        def count_reachable_edges_iterative(start_node, initial_battery):
            """Version itérative de count_reachable_edges utilisant une pile"""
            reachable_edges = 0
            visited_edges = set()
            stack = [(start_node, initial_battery, set())]
            visited_nodes = set()

            while stack:
                current, remaining_battery, local_visited = stack.pop()
                if current not in visited_nodes:
                    visited_nodes.add(current)

                    for neighbor in G.neighbors(current):
                        edge = (min(current, neighbor), max(current, neighbor))
                        if edge not in visited_edges:
                            edge_length = G[current][neighbor]['length']
                            if edge_length <= remaining_battery:
                                visited_edges.add(edge)
                                reachable_edges += 1
                                new_battery = remaining_battery - edge_length
                                if new_battery > 0 and neighbor not in visited_nodes:
                                    stack.append((neighbor, new_battery, visited_edges))

            return reachable_edges

        current_batch = []
        for node in G.nodes():
            print(f"Analyse du nœud {node} ({nodes_processed}/{total_nodes})...")
            score = 0

            # Critère 1 : Nombre de voisins directs et jusqu'à profondeur 5
            depth_neighbors = count_neighbors_at_depth(G, node, 5, dataset['batteryCapacity'])
            num_neighbors = depth_neighbors[1]  # Voisins directs
            score += num_neighbors * 10
            all_num_neighbors = 0

            # Bonus pour les voisins à différentes profondeurs
            for depth, count in depth_neighbors.items():
                all_num_neighbors += count
                score += count * (10 / depth)

            # Critère 2 : Centralité du nœud
            try:
                paths = nx.single_source_dijkstra_path_length(G, node, weight='length')
                avg_distance = sum(paths.values()) / len(paths)
                centrality_score = (dataset['batteryCapacity'] / (avg_distance + 1)) * 20
                score += centrality_score
            except:
                continue

            # Critère 3 : Routes accessibles (version itérative)
            reachable_edges = count_reachable_edges_iterative(node, dataset['batteryCapacity'])
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

            current_batch.append((node, nodes_analysis[node]))
            nodes_processed += 1

            # Mise à jour périodique du classement
            if nodes_processed % update_frequency == 0:
                # Trier le batch courant
                sorted_batch = sorted(current_batch, key=lambda x: x[1]['score'], reverse=True)
                # Prendre les 20 meilleurs du batch
                top_batch = sorted_batch[:20]
                # Mettre à jour le fichier de classement
                update_ranking_file(top_batch)
                # Vider le batch courant
                current_batch = []

                # Afficher la progression
                progress = (nodes_processed / total_nodes) * 100
                print(f"⏳ Progression: {progress:.1f}% ({nodes_processed}/{total_nodes} nœuds)")

        # Traiter le dernier batch s'il en reste
        if current_batch:
            sorted_batch = sorted(current_batch, key=lambda x: x[1]['score'], reverse=True)
            top_batch = sorted_batch[:20]
            update_ranking_file(top_batch)

        # Retourner le classement final
        with open(ranking_file, 'r') as f:
            final_ranking = json.load(f)

        # Convertir le format pour maintenir la compatibilité avec le code existant
        return [(entry['node_id'], entry['stats']) for entry in final_ranking]

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
        cache_file = f'{cache_dir}/final_base_nodes_cache_{dataset_file}.json'

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
        cached_nodes = NodeAnalyser.get_cached_base_nodes(dataset_file)
        if cached_nodes is None:
            # Si le cache n'est pas accessible, calculer les noeuds
            cached_nodes = NodeAnalyser.analyze_base_nodes(G, dataset, dataset_file)
            # Essayer de sauvegarder dans le cache
            NodeAnalyser.save_cached_base_nodes(dataset_file, cached_nodes)

        # Retourner un noeud au hasard parmi les meilleurs
        random_node = random.choice(cached_nodes)
        print(f"\nChosen base node {random_node[0]} with score {random_node[1]['score']:.2f}")
        return int(random_node[0])

    @staticmethod
    def get_daily_scores(solution_txt, dataset_txt):
        """
        Calcule les scores cumulatifs pour chaque jour de la solution
        """
        dataset = json.loads(dataset_txt)
        solution = json.loads(solution_txt)

        # Initialisation
        base_id = solution['chargeStationId']
        itinerary = solution['itinerary']

        # Création du dictionnaire des longueurs des routes
        edge_length = {}
        for road in dataset['roads']:
            edge_length[(road['intersectionId1'], road['intersectionId2'])] = road['length']
            if not road['isOneWay']:
                edge_length[(road['intersectionId2'], road['intersectionId1'])] = road['length']

        # Variables pour le suivi
        daily_scores = []
        visited_edges = set()
        cumulative_score = 0
        remaining_battery = dataset['batteryCapacity']

        # Parcours de l'itinéraire
        for i in range(len(itinerary) - 1):
            n1, n2 = itinerary[i], itinerary[i + 1]

            # Nouveau jour
            if n1 == base_id and i > 0:
                daily_scores.append(cumulative_score)
                remaining_battery = dataset['batteryCapacity']

            # Mise à jour de la batterie
            edge_dist = edge_length.get((n1, n2), float('inf'))
            remaining_battery -= edge_dist

            # Si la batterie est épuisée, on arrête le calcul pour ce jour
            if remaining_battery < 0:
                daily_scores.append(cumulative_score)
                break

            # Calcul du score pour les nouvelles routes
            if (n1, n2) not in visited_edges:
                cumulative_score += edge_dist
                visited_edges.add((n1, n2))
                visited_edges.add((n2, n1))

        # Ajouter le dernier jour si nécessaire
        if not daily_scores or daily_scores[-1] != cumulative_score:
            daily_scores.append(cumulative_score)

        # Vérifier si toutes les routes ont été couvertes
        total_length = sum(road['length'] for road in dataset['roads'])

        if cumulative_score == total_length:
            # Calculer le bonus pour finition précoce
            days_used = len(daily_scores)
            remaining_days = dataset['numDays'] - days_used
            battery_ratio = remaining_battery / dataset['batteryCapacity']
            bonus = (remaining_days + battery_ratio) / dataset['numDays'] + 1

            # Appliquer le bonus au score final
            final_score = math.ceil(cumulative_score * bonus)
            if daily_scores:
                daily_scores[-1] = final_score

        return daily_scores