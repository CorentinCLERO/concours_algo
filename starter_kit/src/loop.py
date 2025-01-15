import os
import glob
import json
import test_solution
import datetime
import networkx as nx
from src.analyser import Analyser
from src.solver.solver import Solver
from src.save_score import SaveScore
from src.node_analyser import NodeAnalyser

class Loop:

    def loop(dataset, dataset_file, max_attempts, depth_number):
        # Création d'un graphe orienté vide
        G = nx.DiGraph()

        dataset_json = json.loads(dataset)

        # Construction du graphe à partir des routes du dataset
        for edge in dataset_json['roads']:
            if edge['isOneWay']:
                # Pour les routes à sens unique
                G.add_edge(edge['intersectionId1'], edge['intersectionId2'],
                        length=edge['length'], one_way=True)
            else:
                # Pour les routes à double sens
                G.add_edge(edge['intersectionId1'], edge['intersectionId2'],
                        length=edge['length'], one_way=False)
                G.add_edge(edge['intersectionId2'], edge['intersectionId1'],
                        length=edge['length'], one_way=False)

        # Charger le dataset et obtenir le nombre de routes
        roads_length = len(dataset_json['roads'])
        print(f"Dataset {dataset_file} contains {roads_length} roads")

        highest_existing_score = Analyser.get_highest_score_from_files(dataset_file)
        best_result = None
        best_score = 0
        attempt = 0

        while attempt < max_attempts:
            # Sélection du nœud de base optimal avec vérification de sa validité
            base_id = NodeAnalyser.find_best_base(G, dataset_json, dataset_file)

            # Vérification de la validité du nœud de base
            if not G.has_node(base_id):
                print(f"Error: Base node {base_id} not found in graph")
                return json.dumps({"chargeStationId": base_id, "itinerary": [base_id]})

            print(f"\nAttempt {attempt + 1}/{max_attempts}")
            solution = Solver.solve(dataset, depth_number, dataset_file, base_id, G, best_score)

            # Si la solution retournée est minimale, c'est qu'on doit réessayer avec une nouvelle base
            if solution == json.dumps({"chargeStationId": base_id, "itinerary": [base_id]}):
                print("🔄 Restarting with new base node...")
                attempt += 1
                continue

            score, is_valid, message = test_solution.getSolutionScore(solution, dataset)

            # Sauvegarder dans l'historique
            history = SaveScore.save_score_history(dataset_file, depth_number, score, is_valid, roads_length)

            if is_valid:
                if score > best_score:
                    best_score = score
                    best_result = solution

                    if score > highest_existing_score:
                        highest_existing_score = score
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

                # Incrémenter le compteur de tentatives seulement si la solution est valide
                attempt += 1
            else:
                print(f'❌ Invalid solution: {message}')

            # Afficher les stats périodiquement
            if attempt > 0 and attempt % 10 == 0:
                stats = history['stats']
                print(f"\n📊 Current Statistics (Depth {depth_number}):")
                print(f"Highest Score: {stats['highest_score']}")
                print(f"Lowest Valid Score: {stats['lowest_score']}")
                print(f"Valid/Total Attempts: {stats['valid_attempts']}/{stats['total_attempts']}")

        print(f'\n🏁 Final best score: {best_score} highest existing score : {highest_existing_score}')
        return best_score