import json
import random
import networkx as nx
from src.node_analyser import NodeAnalyser

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

        def evaluate_path(G, path, curr_battery, visited_roads, dist_to_base, dataset, depth):
            """Évalue un chemin possible en fonction de plusieurs critères

            Args:
                G: Le graphe
                path: Liste des nœuds du chemin à évaluer
                curr_battery: Niveau de batterie actuel
                visited_roads: Ensemble des routes déjà visitées
                dist_to_base: Dictionnaire des distances à la base
                dataset: Données du problème
                depth: Profondeur actuelle dans la recherche

            Returns:
                float: Score d'évaluation du chemin
            """
            total_score = 0
            remaining_battery = curr_battery
            current_visited = visited_roads.copy()  # Copie pour ne pas modifier l'original

            # Évaluation de chaque segment du chemin
            for i in range(len(path)-1):
                node1, node2 = path[i], path[i+1]

                # Vérification de l'existence de l'arête
                if not G.has_edge(node1, node2):
                    return float('-inf')

                edge_len = G[node1][node2]['length']

                # Vérification de la faisabilité énergétique
                if remaining_battery < edge_len:
                    return float('-inf')

                remaining_battery -= edge_len

                # Bonus pour les routes non visitées (diminue avec la profondeur)
                if (node1, node2) not in current_visited:
                    total_score += 100 * (1 / (depth + 1))
                    current_visited.add((node1, node2))

                # Bonus proportionnel à la longueur de la route
                total_score += edge_len / 10

                # Bonus pour les voisins non visités du prochain nœud
                unvisited_neighbors = sum(1 for neighbor in G.neighbors(node2)
                                        if (node2, neighbor) not in current_visited)
                total_score += unvisited_neighbors * 5 * (1 / (depth + 1))

                # Vérification que le nœud est connecté à la base
                if node2 not in dist_to_base:
                    return float('-inf')

                # Pénalité si on ne peut pas rentrer à la base
                if remaining_battery < dist_to_base[node2]:
                    total_score -= 1000

                # Pénalité pour retour non nécessaire à la base
                if node2 == base_id and remaining_battery > dataset['batteryCapacity'] / 10:
                    total_score -= 500

            return total_score

        def find_best_path(G, curr_node, battery_remaining, visited_roads, dist_to_base, dataset, depth=0, max_depth=3):
            """Trouve le meilleur chemin possible à partir du nœud actuel

            Args:
                G: Le graphe
                curr_node: Nœud de départ
                battery_remaining: Niveau de batterie restant
                visited_roads: Ensemble des routes déjà visitées
                dist_to_base: Dictionnaire des distances à la base
                dataset: Données du problème
                depth: Profondeur actuelle dans la recherche
                max_depth: Profondeur maximale de recherche

            Returns:
                tuple: (meilleur_chemin, meilleur_score)
            """
            # Condition d'arrêt de la récursion
            if depth >= max_depth:
                return [], 0

            best_path = []
            best_score = float('-inf')

            try:
                # Récupération et mélange des voisins pour diversifier la recherche
                neighbors = list(G.neighbors(curr_node))
                for next_node in neighbors:
                    # Vérification de la validité de l'arête
                    if not G.has_edge(curr_node, next_node):
                        continue

                    edge_len = G[curr_node][next_node]['length']

                    # Vérification de la faisabilité énergétique
                    if battery_remaining >= edge_len:
                        # Évaluation du chemin direct
                        path = [curr_node, next_node]
                        score = evaluate_path(G, path, battery_remaining, visited_roads, dist_to_base, dataset, depth)

                        # Exploration récursive des chemins plus longs
                        if depth < max_depth - 1:
                            next_battery = battery_remaining - edge_len
                            next_visited = visited_roads.copy()
                            if (curr_node, next_node) not in next_visited:
                                next_visited.add((curr_node, next_node))

                            # Recherche récursive du meilleur sous-chemin
                            sub_path, sub_score = find_best_path(G, next_node, next_battery, next_visited,
                                                            dist_to_base, dataset, depth + 1, max_depth)

                            # Combinaison des chemins si un sous-chemin a été trouvé
                            if sub_path:
                                path.extend(sub_path[1:])
                                # Le score du sous-chemin est pondéré par la profondeur
                                score += sub_score * (0.8 ** depth)

                        # Mise à jour du meilleur chemin si nécessaire
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

        # Boucle principale sur chaque jour
        for day_i in range(dataset['numDays']):
            battery_remaining = dataset['batteryCapacity']
            failed_attempts = 0  # Compteur pour les tentatives échouées

            # Boucle de déplacement pour la journée
            while True:
                try:
                    # Si trop de tentatives échouées, force le retour à la base
                    if failed_attempts >= 3:
                        print(f"Too many failed attempts, forcing return to base")
                        # Trouver le plus court chemin vers la base
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
                        print(f"Warning: Node {curr_node} has no neighbors, returning to base")
                        next_node = base_id
                    else:
                        random.shuffle(neighbors)
                        best_path, _ = find_best_path(G, curr_node, battery_remaining, visited_roads,
                                                    dist_to_base, dataset, depth=0, max_depth=depth_complexity)

                        if best_path and len(best_path) > 1:
                            next_node = best_path[1]
                        else:
                            next_node = base_id

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

                    # Marquage des routes comme visitées
                    visited_roads.add((curr_node, next_node))
                    visited_roads.add((next_node, curr_node))

                    # Mise à jour de la batterie et de la position
                    battery_remaining -= G[curr_node][next_node]['length']
                    path.append(next_node)
                    curr_node = next_node

                    # Fin de la journée si retour à la base
                    if curr_node == base_id:
                        break

                except Exception as e:
                    print(f"Error during path finding: {e}")
                    failed_attempts += 1
                    if failed_attempts >= 3:
                        print(f"Too many errors, forcing end of day")
                        path.append(base_id)
                        curr_node = base_id
                        break

            print(f'End day {day_i+1} with {battery_remaining} battery')

        # Affichage des statistiques finales
        print(f'Visited {len(visited_roads) // 2} / {len(dataset["roads"])} roads')
        print(f'Expected score: {score:_}')

        # Retour de la solution au format JSON
        return json.dumps({"chargeStationId": base_id, "itinerary": path})