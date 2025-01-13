import os
import glob
import json
import random
import networkx as nx
import test_solution
import datetime


def solve(dataset_txt):
    # Lecture du dataset
    dataset = json.loads(dataset_txt)

    # Choix de la station de charge : on prend l'intersection 0 par défaut. Il y a peut-être mieux à faire !
    base_id = 0

    # On crée le graphe du réseau avec networkx. On aurait pu le faire aussi avec un simple dictionnaire Python
    # networkx permet cependant d'avoir accès à certaines fonctions comme le calcul des distances plutôt que de les recoder
    G = nx.DiGraph()
    for edge in dataset['roads']:
        if edge['isOneWay']:
            G.add_edge(edge['intersectionId1'], edge['intersectionId2'], length=edge['length'], one_way=True)
        else:
            G.add_edge(edge['intersectionId1'], edge['intersectionId2'], length=edge['length'], one_way=False)
            G.add_edge(edge['intersectionId2'], edge['intersectionId1'], length=edge['length'], one_way=False)


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

            # Pour chaque voisin possible
            for nxt in neighbors:
                edge_len = G[curr_node][nxt]['length']  # Longueur de la route vers ce voisin

                # Vérification différente selon si c'est le dernier jour ou non
                can_move = False
                if day_i == dataset['numDays'] - 1:
                    # Dernier jour : vérifier si on peut aller au nœud ET revenir à la base si nécessaire
                    if nxt == base_id:
                        can_move = battery_remaining >= edge_len
                    else:
                        distance_to_base = dist_to_base[nxt]
                        can_move = battery_remaining >= (edge_len + distance_to_base)
                else:
                    # Autres jours : on vérifie si on peut aller au nœud ET rentrer à la base
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

                    # Priorité 5: Gestion différente selon le jour
                    if day_i == dataset['numDays'] - 1:
                        # Dernier jour : favoriser les routes non visitées proches
                        if (curr_node, nxt) not in visited_roads:
                            priority += 50
                    else:
                        # Autres jours : équilibrer entre exploration et gestion de la batterie
                        if dist_to_base[nxt] < dataset['batteryCapacity'] / 3:
                            priority += 10  # Bonus pour les nœuds permettant plus d'exploration

                    # Mise à jour du meilleur nœud si la priorité est plus élevée
                    if priority > best_priority:
                        best_priority = priority
                        next_node = nxt

            # Si aucun nœud valide n'a été trouvé ou si la batterie est critique
            if next_node is None or battery_remaining - G[curr_node][next_node]['length'] < dist_to_base[next_node]:
                # Retour forcé à la base
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

            # Vérification finale de sécurité
            if next_node is None or (next_node != base_id and
                battery_remaining - G[curr_node][next_node]['length'] < dist_to_base[next_node]):
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

# dataset_file = "1_example"
dataset_file = "2_pacman"
# dataset_file = "3_efrei"
# dataset_file = "4_manhattan"
# dataset_file = "5_gta"
# dataset_file = "6_paris"
# dataset_file = "7_london"
dataset = open(f'.\\datasets\\{dataset_file}.json').read()
scoreAttempded = 120

def loop():
    max_attempts = 10000
    best_score = 0
    best_result = None
    is_result_find = False

    for attempt in range(max_attempts):
        solution = solve(dataset)
        score, is_valid, message = test_solution.getSolutionScore(solution, dataset)

        # if is_valid and score >= scoreAttempded:
        #     print('✅ Solution is valid!')
        #     print(f'Message: {message}')
        #     print(f'Score: {score:_}')
        #     is_result_find = True

        #     break

        if score > best_score:
            best_score = score
            best_result = solution

        print(f'Attempt {attempt + 1}: Score = {score}')

    if not is_result_find:
        print(f'❌ Could not find solution better than {scoreAttempded} after {max_attempts} attempts')
        print(f'Best score achieved: {best_score}')

    # Vérifie si la meilleure solution trouvée est meilleure que les solutions existantes
    highest_existing_score = get_highest_score_from_files(dataset_file)

    if best_score > highest_existing_score:
        print(f'New best score! (Previous best: {highest_existing_score})')
        date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f'{dataset_file}_{best_score}_{date}'

        with open(f'.\\solutions\\{file_name}.json', 'w') as f:
            f.write(best_result)
        print('Best solution saved')
    else:
        print(f'No new best score. Current best remains: {highest_existing_score}')

print('---------------------------------')
print(f'Solving {dataset_file}')
loop()