import json
import random
import networkx as nx
from src.node_analyser import NodeAnalyser
import datetime

class Solver:
    @staticmethod
    def solve(dataset_txt, depth_complexity, dataset_file):
        # Conversion du JSON en dictionnaire Python
        dataset = json.loads(dataset_txt)

        # Création d'un graphe orienté vide
        G = nx.DiGraph()

        # Construction du graphe à partir des routes du dataset
        for edge in dataset['roads']:
            if edge['isOneWay']:
                # Pour les routes à sens unique, on ajoute une seule arête
                G.add_edge(edge['intersectionId1'], edge['intersectionId2'],
                          length=edge['length'], one_way=True)
            else:
                # Pour les routes à double sens, on ajoute deux arêtes (une dans chaque sens)
                G.add_edge(edge['intersectionId1'], edge['intersectionId2'],
                          length=edge['length'], one_way=False)
                G.add_edge(edge['intersectionId2'], edge['intersectionId1'],
                          length=edge['length'], one_way=False)

        # Sélection du nœud de base optimal avec vérification de sa validité
        base_id = NodeAnalyser.find_best_base(G, dataset, dataset_file)
        if not G.has_node(base_id) or len(list(G.neighbors(base_id))) == 0:
            print(f"Warning: Invalid base node {base_id}, falling back to node 0")
            base_id = 0  # Repli sur le nœud 0 si le nœud choisi n'est pas valide

        # Calcul des plus courts chemins vers la base avec gestion d'erreur
        try:
            # Création d'un dictionnaire des distances minimales vers la base
            dist_to_base = nx.shortest_path_length(G, source=None, target=base_id, weight='length')
        except nx.NetworkXError:
            print(f"Error: Cannot compute paths to base node {base_id}")
            # Retour d'une solution minimale en cas d'erreur
            return json.dumps({"chargeStationId": base_id, "itinerary": [base_id]})

        def evaluate_path(G, path, curr_battery, visited_roads, dist_to_base, dataset, depth, is_last_day=False):
            total_score = 0
            remaining_battery = curr_battery
            current_visited = visited_roads.copy()

            for i in range(len(path)-1):
                node1, node2 = path[i], path[i+1]

                if not G.has_edge(node1, node2):
                    return float('-inf')

                edge_len = G[node1][node2]['length']

                if remaining_battery < edge_len:
                    return float('-inf')

                remaining_battery -= edge_len

                # Bonus pour les routes non visitées
                if (node1, node2) not in current_visited:
                    if is_last_day:
                        # Bonus plus important le dernier jour
                        total_score += 150 * (1 / (depth + 1))
                        # Bonus supplémentaire pour l'utilisation de batterie
                        total_score += (edge_len / dataset['batteryCapacity']) * 200
                    else:
                        total_score += 100 * (1 / (depth + 1))
                    current_visited.add((node1, node2))

                # Bonus pour l'utilisation efficace de la batterie le dernier jour
                if is_last_day:
                    battery_efficiency = edge_len / dataset['batteryCapacity']
                    total_score += battery_efficiency * 100

                # Autres bonus existants...
                total_score += edge_len / 10
                unvisited_neighbors = sum(1 for neighbor in G.neighbors(node2)
                                        if (node2, neighbor) not in current_visited)
                total_score += unvisited_neighbors * 5 * (1 / (depth + 1))

                # Conditions pour les jours non-derniers
                if not is_last_day:
                    if node2 not in dist_to_base:
                        return float('-inf')
                    if remaining_battery < dist_to_base[node2]:
                        total_score -= 1000
                    if node2 == base_id and remaining_battery > dataset['batteryCapacity'] / 100:
                        total_score -= 500

            return total_score

        def find_best_path(G, curr_node, battery_remaining, visited_roads, dist_to_base, dataset, depth=0, max_depth=3, is_last_day=False):
            """Version modifiée pour maximiser l'utilisation de la batterie le dernier jour"""
            if depth >= max_depth:
                return [], 0

            best_path = []
            best_score = float('-inf')

            try:
                neighbors = list(G.neighbors(curr_node))

                if is_last_day and depth == 0:
                    # Calcul des scores heuristiques pour le dernier jour
                    neighbor_scores = []
                    for n in neighbors:
                        if G.has_edge(curr_node, n) and battery_remaining >= G[curr_node][n]['length']:
                            heuristic_score = 0
                            edge_len = G[curr_node][n]['length']

                            # Bonus pour les routes non visitées
                            if (curr_node, n) not in visited_roads:
                                heuristic_score += 1000

                            # Bonus pour maximiser l'utilisation de la batterie
                            battery_usage_ratio = edge_len / battery_remaining
                            heuristic_score += battery_usage_ratio * 500  # Favorise les routes qui utilisent plus de batterie

                            # Bonus pour les routes qui mènent à plus de routes non visitées
                            unvisited_connections = sum(1 for neighbor in G.neighbors(n)
                                                    if (n, neighbor) not in visited_roads and
                                                    battery_remaining - edge_len >= G[n][neighbor]['length'])
                            heuristic_score += unvisited_connections * 200

                            # Bonus pour les chemins qui permettent d'utiliser toute la batterie
                            remaining_after_move = battery_remaining - edge_len
                            possible_subsequent_moves = sum(1 for neighbor in G.neighbors(n)
                                                        if G.has_edge(n, neighbor) and
                                                        remaining_after_move >= G[n][neighbor]['length'])
                            heuristic_score += possible_subsequent_moves * 100

                            neighbor_scores.append((n, heuristic_score))

                    # Trier les voisins par score heuristique décroissant
                    neighbors = [n for n, _ in sorted(neighbor_scores, key=lambda x: -x[1])]

                for next_node in neighbors:
                    if not G.has_edge(curr_node, next_node):
                        continue

                    edge_len = G[curr_node][next_node]['length']
                    if battery_remaining >= edge_len:
                        path = [curr_node, next_node]

                        # Calcul du score avec bonus pour utilisation de batterie le dernier jour
                        if is_last_day:
                            battery_usage = edge_len / dataset['batteryCapacity']
                            score = evaluate_path(G, path, battery_remaining, visited_roads,
                                            dist_to_base, dataset, depth, is_last_day)
                            score += battery_usage * 1000  # Bonus pour utilisation de batterie
                        else:
                            score = evaluate_path(G, path, battery_remaining, visited_roads,
                                            dist_to_base, dataset, depth, is_last_day)

                        if depth < max_depth - 1:
                            next_battery = battery_remaining - edge_len
                            next_visited = visited_roads.copy()
                            if (curr_node, next_node) not in next_visited:
                                next_visited.add((curr_node, next_node))

                            sub_path, sub_score = find_best_path(
                                G, next_node, next_battery, next_visited,
                                dist_to_base, dataset, depth + 1, max_depth,
                                is_last_day
                            )

                            if sub_path:
                                path.extend(sub_path[1:])
                                if is_last_day:
                                    # Augmenter l'importance des sous-chemins le dernier jour
                                    score += sub_score * (0.95 ** depth)
                                else:
                                    score += sub_score * (0.8 ** depth)

                        if score > best_score:
                            best_score = score
                            best_path = path

            except Exception as e:
                print(f"Error in find_best_path: {e}")
                return [], 0

            return best_path, best_score

        # Initialisation des variables de suivi
        visited_roads = set()  # Ensemble des routes visitées
        curr_node = base_id    # Position actuelle (commence à la base)
        path = [base_id]       # Chemin parcouru
        score = 0             # Score total
        time = datetime.datetime.now().isoformat()

        # Boucle principale sur chaque jour
        for day_i in range(dataset['numDays']):
            battery_remaining = dataset['batteryCapacity']
            failed_attempts = 0  # Compteur pour les tentatives échouées
            is_last_day = day_i == dataset['numDays'] - 1

            # Boucle de déplacement pour la journée
            while True:
                try:
                    # Si trop de tentatives échouées
                    if failed_attempts >= 3:
                        if not is_last_day:  # Seulement si ce n'est pas le dernier jour
                            print(f"Too many failed attempts, forcing return to base")
                            try:
                                shortest_path = nx.shortest_path(G, curr_node, base_id, weight='length')
                                for node in shortest_path[1:]:
                                    path.append(node)
                                    if (curr_node, node) not in visited_roads:
                                        score += G[curr_node][node]['length']
                                    visited_roads.add((curr_node, node))
                                    visited_roads.add((node, curr_node))
                                    curr_node = node
                            except nx.NetworkXNoPath:
                                print(f"No path to base found, teleporting to base")
                                path.append(base_id)
                                curr_node = base_id
                        break

                    neighbors = list(G.neighbors(curr_node))
                    if not neighbors:
                        if not is_last_day:  # Seulement si ce n'est pas le dernier jour
                            print(f"Warning: Node {curr_node} has no neighbors, returning to base")
                            next_node = base_id
                        else:
                            break
                    else:
                        random.shuffle(neighbors)
                        best_path, _ = find_best_path(G, curr_node, battery_remaining, visited_roads,
                                                    dist_to_base, dataset, depth=0, max_depth=depth_complexity,
                                                    is_last_day=is_last_day)

                        if best_path and len(best_path) > 1:
                            next_node = best_path[1]
                        else:
                            if not is_last_day:
                                next_node = base_id
                            else:
                                break

                    # Vérification de sécurité pour l'arête
                    if not G.has_edge(curr_node, next_node):
                        print(f"Warning: Invalid edge {curr_node}->{next_node}, returning to base")
                        failed_attempts += 1
                        continue

                    # Réinitialisation du compteur d'échecs si le mouvement est valide
                    failed_attempts = 0

                    # Mise à jour du score pour les nouvelles routes
                    if (curr_node, next_node) not in visited_roads:
                        score += G[curr_node][next_node]['length']

                        if datetime.datetime.now() - datetime.datetime.fromisoformat(time) > datetime.timedelta(seconds=5):
                            print(f"😴 It's been a while so the current score: {score}")
                            time = datetime.datetime.now().isoformat()

                    # Marquage des routes comme visitées
                    visited_roads.add((curr_node, next_node))
                    visited_roads.add((next_node, curr_node))

                    # Mise à jour de la batterie et de la position
                    battery_remaining -= G[curr_node][next_node]['length']
                    path.append(next_node)
                    curr_node = next_node

                    # Fin de la journée si retour à la base (sauf dernier jour)
                    if not is_last_day and curr_node == base_id:
                        break
                    # Pour le dernier jour, on continue jusqu'à épuisement de la batterie
                    elif is_last_day:
                        # Vérifier s'il reste assez de batterie pour au moins une route non visitée
                        min_edge_length = float('inf')
                        for n in G.neighbors(curr_node):
                            if G.has_edge(curr_node, n):
                                min_edge_length = min(min_edge_length, G[curr_node][n]['length'])

                        if battery_remaining < min_edge_length or not any(
                            G.has_edge(curr_node, n) and battery_remaining >= G[curr_node][n]['length']
                            for n in G.neighbors(curr_node)
                        ):
                            print(f"No more feasible moves with remaining battery: {battery_remaining}")
                            break

                except Exception as e:
                    print(f"Error during path finding: {e}")
                    failed_attempts += 1
                    if failed_attempts >= 3:
                        print(f"Too many errors, forcing end of day")
                        path.append(base_id)
                        curr_node = base_id
                        break

            print(f'End day {day_i+1} with {battery_remaining} battery and score {score:_}')

        # Affichage des statistiques finales
        print(f'Visited {len(visited_roads) // 2} / {len(dataset["roads"])} roads')
        print(f'Expected score: {score:_}')

        # Retour de la solution au format JSON
        return json.dumps({"chargeStationId": base_id, "itinerary": path})