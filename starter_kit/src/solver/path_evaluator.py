import random

class PathEvaluator:
    """Classe responsable de l'évaluation des chemins et du calcul des scores"""

    @staticmethod
    def find_best_path(G, curr_node, curr_battery, visited_roads, dist_to_base, dataset, depth, max_depth, is_last_day=False):
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

        random.shuffle(neighbors)

        for next_node in neighbors:
            if not G.has_edge(curr_node, next_node):
                continue

            edge_len = G[curr_node][next_node]['length']
            if curr_battery < edge_len:
                continue

            # Vérification du retour à la base si nécessaire
            if not is_last_day:
                if next_node not in dist_to_base:
                    continue
                if curr_battery - edge_len < dist_to_base[next_node]:
                    continue

            # Construction du chemin candidat
            candidate_path = [curr_node, next_node]
            remaining_battery = curr_battery - edge_len
            temp_visited = visited_roads.copy()
            temp_visited.add((curr_node, next_node))
            temp_visited.add((next_node, curr_node))

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

        for i in range(len(path)-1):
            node1, node2 = path[i], path[i+1]

            if not G.has_edge(node1, node2):
                return float('-inf')

            edge_len = G[node1][node2]['length']
            if remaining_battery < edge_len:
                return float('-inf')

            remaining_battery -= edge_len

            # Score pour routes non visitées
            if (node1, node2) not in current_visited:
                total_score += 10  # Score de base pour nouvelle route
                if is_last_day:
                    total_score += 5  # Bonus pour dernier jour
                current_visited.add((node1, node2))
                current_visited.add((node2, node1))

            # Bonus pour utilisation efficace de la batterie
            battery_efficiency = edge_len / dataset['batteryCapacity']
            total_score += battery_efficiency * 2

            # Bonus pour exploration
            unvisited_neighbors = sum(1 for n in G.neighbors(node2)
                                    if (node2, n) not in current_visited)
            total_score += unvisited_neighbors * (1 / (depth + 1))

        return total_score