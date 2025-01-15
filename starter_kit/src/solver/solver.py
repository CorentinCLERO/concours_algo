import json
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
        """Charge les meilleurs scores existants"""
        if not dataset_file:
            return None
        try:
            pattern = f'.\\solutions\\{dataset_file}_*.json'
            best_solution = None
            for solution_file in glob.glob(pattern):
                with open(solution_file, 'r') as f:
                    solution = f.read()
                    score = int(solution_file.split('_')[2])
                    if score > best_score:
                        best_score = score
                        best_solution = solution

            if best_solution:
                best_daily_scores = NodeAnalyser.get_daily_scores(best_solution, dataset_txt)
                print(f"Best existing daily scores: {best_daily_scores}")
                return best_daily_scores
        except Exception as e:
            print(f"Warning: Could not load best solution: {e}")
            return None