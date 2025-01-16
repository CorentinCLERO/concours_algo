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

            # Empêcher d'aller à la base le dernier jour
            if is_last_day and n == base_id:
                continue

            edge_len = G[curr_node][n]['length']
            if curr_battery < edge_len:
                continue

            # Vérification de la batterie pour le retour à la base
            if n == base_id and not is_last_day:
                battery_percentage = (curr_battery / dataset['batteryCapacity']) * 100
                if battery_percentage > 10:  # Impossible de rentrer avec plus de 10%
                    continue

            if not is_last_day:
                if n not in dist_to_base or curr_battery - edge_len < dist_to_base[n]:
                    continue

            # Score du voisin basé sur plusieurs facteurs
            unvisited_count = sum(1 for next_n in G.neighbors(n) if (n, next_n) not in visited_roads)
            battery_efficiency = 1 - (edge_len / curr_battery)
            distance_to_base = dist_to_base.get(n, float('inf')) if not is_last_day else 0

            neighbor_score = (
                unvisited_count * 150 +  # Augmentation de l'importance des routes non visitées
                battery_efficiency * 70 +  # Plus d'importance à l'efficacité
                (1 / (distance_to_base + 1)) * 40 +  # Distance à la base
                len(list(G.neighbors(n))) * 20 +  # Bonus pour les nœuds bien connectés
                (edge_len / dataset['batteryCapacity']) * 30  # Bonus pour les longues routes
            )

            # Bonus pour les zones peu explorées
            area_exploration = sum(1 for nn in G.neighbors(n)
                                for nnn in G.neighbors(nn)
                                if (nn, nnn) not in visited_roads)
            neighbor_score += area_exploration * 15

            # Pénalité pour retour à la base avec plus de 5% de batterie
            if n == base_id and not is_last_day:
                battery_percentage = (curr_battery / dataset['batteryCapacity']) * 100
                if battery_percentage > 5:
                    neighbor_score *= 0.1  # Très forte pénalité (90% de réduction)

            if (curr_node, n) not in visited_roads:
                neighbor_score *= 2

            neighbor_scores.append((n, neighbor_score))

        # Tri des voisins par score
        if neighbor_scores:
            neighbor_scores.sort(key=lambda x: x[1], reverse=True)

            # Sélection des meilleurs voisins avec un peu d'aléatoire
            top_k = min(5, len(neighbor_scores))
            selected_neighbors = neighbor_scores[:top_k]
            weights = [1/(i+1) for i in range(top_k)]
            selected_neighbors = random.choices(selected_neighbors, weights=weights, k=min(3, top_k))
            neighbors = [n[0] for n in selected_neighbors]
        else:
            return [curr_node], 0

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
                    depth + 1, max_depth, base_id, is_last_day
                )
                if len(sub_path) > 1:
                    candidate_path.extend(sub_path[1:])

            # Évaluation du score
            path_score = PathEvaluator.evaluate_path(
                G, candidate_path,
                curr_battery, visited_roads,
                dist_to_base, dataset,
                depth, max_depth,
                base_id, is_last_day
            )

            if path_score > best_score:
                best_score = path_score
                best_path = candidate_path

        return best_path, best_score

    @staticmethod
    def evaluate_path(G, path, curr_battery, visited_roads, dist_to_base, dataset, depth, max_depth, base_id, is_last_day=False):
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

            # Bonus pour la couverture de zones
            zone_coverage = len(set(n for p in path for n in G.neighbors(p))) / len(G.nodes())
            total_score *= (1 + zone_coverage)

            # Bonus pour l'efficacité du chemin
            path_efficiency = len(set(path)) / len(path)  # Pénalise les allers-retours
            total_score *= path_efficiency

            # Bonus pour la batterie restante le dernier jour
            if is_last_day:
                battery_usage = (dataset['batteryCapacity'] - remaining_battery) / dataset['batteryCapacity']
                total_score *= (1 + battery_usage)  # Récompense l'utilisation maximale

            # Vérification du retour à la base
            if node2 == base_id:
                if is_last_day:  # Impossible d'aller à la base le dernier jour
                    return float('-inf')

                battery_percentage = (remaining_battery / dataset['batteryCapacity']) * 100
                if battery_percentage > 10:  # Impossible de rentrer avec plus de 10%
                    return float('-inf')
                elif battery_percentage > 5:  # Forte pénalité entre 5% et 10%
                    total_score *= 0.1

        # Bonus pour la diversité des routes
        if new_roads_count > 0:
            total_score *= (1 + (new_roads_count / len(path)))

        return total_score