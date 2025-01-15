import json
import os
import networkx as nx
import glob
from src.node_analyser import NodeAnalyser
from src.solver.day_simulator import DaySimulator

class Solver:
    """Classe principale pour résoudre le problème de routage"""

    @staticmethod
    def solve(dataset_txt, depth_complexity, dataset_file, base_id, G, best_score):
        """
        Résout le problème de routage pour un dataset donné

        Args:
            dataset_txt: Données du problème au format JSON
            depth_complexity: Profondeur maximale de recherche
            dataset_file: Nom du fichier dataset pour charger les meilleures solutions
            base_id: ID du nœud de base
            G: Graphe NetworkX

        Returns:
            str: Solution au format JSON
        """
        # Chargement et préparation des données
        dataset = json.loads(dataset_txt)

        # Chargement des meilleurs scores journaliers
        best_daily_scores = Solver._load_best_scores(dataset_file, dataset_txt, best_score)

        # Initialisation du graphe et des distances
        try:
            dist_to_base = nx.shortest_path_length(G, source=None, target=base_id, weight='length')
        except nx.NetworkXError:
            print(f"Error: Cannot compute paths to base node {base_id}")
            return json.dumps({"chargeStationId": base_id, "itinerary": [base_id]})

        # Initialisation du simulateur et des variables
        day_simulator = DaySimulator(G, dataset, base_id, depth_complexity, dist_to_base)
        visited_roads = set()
        curr_node = base_id
        path = [base_id]
        score = 0

        # Simulation jour par jour
        for day_i in range(dataset['numDays']):
            print(f"\nDay {day_i + 1}/{dataset['numDays']}")
            battery_remaining = dataset['batteryCapacity']
            is_last_day = day_i == dataset['numDays'] - 1

            curr_node, battery_remaining, visited_roads, path, score, found_better = day_simulator.simulate_day(
                day_i, curr_node, battery_remaining, visited_roads, path, score, best_daily_scores, is_last_day
            )

            if not found_better:
                # Si aucun meilleur score n'a été trouvé après les tentatives
                return json.dumps({"chargeStationId": base_id, "itinerary": [base_id]})

        # Retour de la solution
        return json.dumps({"chargeStationId": base_id, "itinerary": path})

    @staticmethod
    def _load_best_scores(dataset_file, dataset_txt, best_score):
        """
        Charge les meilleurs scores journaliers existants et met à jour le cache si nécessaire
        """
        if not dataset_file:
            print("Warning: No dataset file provided")
            return None

        try:
            solutions_dir = os.path.join('.', 'solutions')
            cache_dir = os.path.join('.', 'cache', 'daily_scores')
            os.makedirs(solutions_dir, exist_ok=True)
            os.makedirs(cache_dir, exist_ok=True)

            def get_cache_filename(score):
                return os.path.join(cache_dir, f'{dataset_file}_{score}_daily_scores.json')

            # Trouver la meilleure solution existante
            solution_pattern = os.path.join(solutions_dir, f'{dataset_file}_*.json')
            best_solution = None
            highest_solution_score = 0

            for solution_file in glob.glob(solution_pattern):
                try:
                    filename = os.path.basename(solution_file)
                    file_score = int(filename.split('_')[2])
                    if file_score > highest_solution_score:
                        highest_solution_score = file_score
                        with open(solution_file, 'r') as f:
                            best_solution = f.read()
                        print(f"Found solution with score: {file_score}")
                except (ValueError, IndexError) as e:
                    print(f"Warning: Invalid solution file {solution_file}: {e}")
                    continue

            # Trouver le cache existant
            cache_pattern = os.path.join(cache_dir, f'{dataset_file}_*_daily_scores.json')
            current_cache_file = None
            current_cache_score = 0

            for cache_file in glob.glob(cache_pattern):
                try:
                    cache_score = int(cache_file.split('_')[-3])  # Extraire le score du nom du cache
                    current_cache_file = cache_file
                    current_cache_score = cache_score
                    print(f"Found cache with score: {cache_score}")
                except (ValueError, IndexError):
                    continue

            # Vérifier si une mise à jour est nécessaire
            should_update_cache = highest_solution_score > current_cache_score

            if should_update_cache:
                try:
                    print(f"Updating cache: solution score {highest_solution_score} > cache score {current_cache_score}")
                    new_daily_scores = NodeAnalyser.get_daily_scores(best_solution, dataset_txt)
                    new_cache_file = get_cache_filename(highest_solution_score)

                    # Sauvegarder les nouveaux scores
                    with open(new_cache_file, 'w') as f:
                        json.dump(new_daily_scores, f)
                    print(f"Created new cache: {new_cache_file}")

                    # Supprimer l'ancien cache s'il existe
                    if current_cache_file and os.path.exists(current_cache_file):
                        os.remove(current_cache_file)
                        print(f"Removed old cache: {current_cache_file}")

                    return new_daily_scores

                except Exception as e:
                    print(f"Warning: Error calculating new daily scores: {e}")
                    return None

            # Utiliser le cache existant
            elif current_cache_file:
                with open(current_cache_file, 'r') as f:
                    print(f"Loading existing cache with score {current_cache_score}")
                    return json.load(f)

            # Créer un nouveau cache si aucun n'existe
            elif best_solution:
                try:
                    daily_scores = NodeAnalyser.get_daily_scores(best_solution, dataset_txt)
                    new_cache_file = get_cache_filename(highest_solution_score)
                    with open(new_cache_file, 'w') as f:
                        json.dump(daily_scores, f)
                    print(f"Created initial cache: {new_cache_file}")
                    return daily_scores
                except Exception as e:
                    print(f"Warning: Error calculating daily scores: {e}")
                    return None

            print("No valid solutions found")
            return None

        except Exception as e:
            print(f"Error in _load_best_scores: {e}")
            return None