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
        Charge les meilleurs scores journaliers existants

        Args:
            dataset_file (str): Nom du fichier dataset sans extension
            dataset_txt (str): Contenu JSON du dataset
            best_score (int): Score actuel à battre
        """
        if not dataset_file:
            print("Warning: No dataset file provided")
            return None

        try:
            # Définir les chemins de recherche
            solutions_dir = os.path.join('.', 'solutions')
            cache_dir = os.path.join('.', 'cache', 'daily_scores')

            # Créer les dossiers s'ils n'existent pas
            os.makedirs(solutions_dir, exist_ok=True)
            os.makedirs(cache_dir, exist_ok=True)

            # Fichier cache pour les scores journaliers
            cache_file = os.path.join(cache_dir, f'{dataset_file}_daily_scores.json')

            # Si le cache existe, le charger
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    print(f"Loading cached daily scores for {dataset_file}")
                    return json.load(f)

            # Pattern pour chercher les fichiers de solutions
            pattern = os.path.join(solutions_dir, f'{dataset_file}_*.json')

            best_solution = None
            highest_existing_score = 0

            # Parcourir tous les fichiers de solutions
            for solution_file in glob.glob(pattern):
                try:
                    filename = os.path.basename(solution_file)
                    file_score = int(filename.split('_')[2].split('.')[0])

                    if file_score > highest_existing_score:
                        highest_existing_score = file_score
                        with open(solution_file, 'r') as f:
                            best_solution = f.read()

                except (ValueError, IndexError) as e:
                    print(f"Warning: Invalid solution file {solution_file}: {e}")
                    continue

            # Si on a trouvé une solution
            if best_solution:
                try:
                    # Calculer les scores journaliers
                    best_daily_scores = NodeAnalyser.get_daily_scores(best_solution, dataset_txt)
                    print(f"Best existing daily scores: {best_daily_scores}")

                    # Sauvegarder les scores journaliers en cache
                    with open(cache_file, 'w') as f:
                        json.dump(best_daily_scores, f)
                    print(f"Saved daily scores to cache: {cache_file}")

                    return best_daily_scores

                except Exception as e:
                    print(f"Warning: Error calculating daily scores: {e}")
                    return None

            print("No valid solutions found")
            return None

        except Exception as e:
            print(f"Error in _load_best_scores: {e}")
            return None