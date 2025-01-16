import random

class PathEvaluator:
    """Classe responsable de l'évaluation des chemins et du calcul des scores"""

    @staticmethod
    def find_best_path(G, curr_node, curr_battery, visited_roads, dist_to_base, dataset, depth, max_depth, base_id, is_last_day=False):
        """
        Trouve le meilleur chemin à partir du nœud actuel

        Returns:
            tuple: (list[int], float) - (meilleur_chemin, meilleur_score)
        """
        if depth >= max_depth:
            return [curr_node], 0

        best_path = [curr_node]
        best_score = float('-inf')
        neighbors = list(G.neighbors(curr_node))

        if not neighbors:
            return [curr_node], 0

        # Calcul plus sophistiqué pour le tri des voisins
        neighbor_scores = []
        for n in neighbors:
            if not G.has_edge(curr_node, n):
                continue

            edge_len = G[curr_node][n]['length']
            if curr_battery < edge_len:
                continue

            if not is_last_day:
                if n not in dist_to_base or curr_battery - edge_len < dist_to_base[n]:
                    continue

            # Score du voisin basé sur plusieurs facteurs
            unvisited_count = sum(1 for next_n in G.neighbors(n) if (n, next_n) not in visited_roads)
            battery_efficiency = 1 - (edge_len / curr_battery)  # Plus c'est court, mieux c'est
            distance_to_base = dist_to_base.get(n, float('inf')) if not is_last_day else 0
            
            neighbor_score = (
                unvisited_count * 100 +  # Priorité aux nœuds avec beaucoup de routes non visitées
                battery_efficiency * 50 +  # Bonus pour l'efficacité énergétique
                (1 / (distance_to_base + 1)) * 30  # Bonus pour la proximité à la base
            )
            
            if (curr_node, n) not in visited_roads:
                neighbor_score *= 2  # Double score pour les routes non visitées

            neighbor_scores.append((n, neighbor_score))

        # Tri des voisins par score
        neighbor_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Sélection des meilleurs voisins avec un peu d'aléatoire
        top_k = min(5, len(neighbor_scores))
        if top_k > 0:
            selected_neighbors = neighbor_scores[:top_k]
            # Ajout d'aléatoire pondéré pour les meilleurs voisins
            weights = [1/(i+1) for i in range(top_k)]  # Poids décroissants
            selected_neighbors = random.choices(selected_neighbors, weights=weights, k=min(3, top_k))
            neighbors = [n[0] for n in selected_neighbors]
        else:
            neighbors = []

        for next_node in neighbors:
            edge_len = G[curr_node][next_node]['length']
            
            # Construction du chemin candidat
            candidate_path = [curr_node, next_node]
            remaining_battery = curr_battery - edge_len
            temp_visited = visited_roads | {(curr_node, next_node), (next_node, curr_node)}

            # Exploration récursive
            if depth + 1 < max_depth:
                sub_path, sub_score = PathEvaluator.find_best_path(
                    G, next_node, remaining_battery,
                    temp_visited, dist_to_base, dataset,
                    depth + 1, max_depth, is_last_day
                )
                if len(sub_path) > 1:
                    candidate_path.extend(sub_path[1:])

            # Évaluation du score
            path_score = PathEvaluator.evaluate_path(
                G, candidate_path,
                curr_battery, visited_roads,
                dist_to_base, dataset,
                depth, max_depth,
                is_last_day
            )

            if path_score > best_score:
                best_score = path_score
                best_path = candidate_path

        return best_path, best_score

    @staticmethod
    def evaluate_path(G, path, curr_battery, visited_roads, dist_to_base, dataset, depth, max_depth, is_last_day=False):
        """Évalue un chemin donné et calcule son score"""
        if not path or len(path) < 2:
            return float('-inf')

        total_score = 0
        remaining_battery = curr_battery
        current_visited = visited_roads.copy()
        new_roads_count = 0
        consecutive_new_roads = 0

        for i in range(len(path)-1):
            node1, node2 = path[i], path[i+1]

            if not G.has_edge(node1, node2):
                return float('-inf')

            edge_len = G[node1][node2]['length']
            if remaining_battery < edge_len:
                return float('-inf')

            remaining_battery -= edge_len

            # Score significativement plus élevé pour les nouvelles routes
            if (node1, node2) not in current_visited:
                new_roads_count += 1
                consecutive_new_roads += 1
                total_score += edge_len * 100  # Augmentation significative du score de base
                if is_last_day:
                    total_score += edge_len * 20  # Bonus pour dernier jour
                current_visited.add((node1, node2))
                current_visited.add((node2, node1))
            else:
                consecutive_new_roads = 0

            # Bonus pour utilisation efficace de la batterie
            battery_efficiency = edge_len / dataset['batteryCapacity']
            total_score += battery_efficiency * 10

            # Bonus pour l'exploration de nouvelles zones
            unvisited_neighbors = sum(1 for n in G.neighbors(node2)
                                    if (node2, n) not in current_visited)
            total_score += unvisited_neighbors * 20  # Augmentation significative du bonus d'exploration

            # Bonus pour les routes consécutives non visitées
            if consecutive_new_roads > 1:
                total_score *= (1 + (consecutive_new_roads * 0.1))

        # Bonus pour la diversité des routes
        if new_roads_count > 0:
            total_score *= (1 + (new_roads_count / len(path)))

        return total_score