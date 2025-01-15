import os
import glob
import json
import test_solution
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from src.solver.solver import Solver

class Analyser:
    def analyze_history(max_attempts, dataset, dataset_file=None, depth_number=None):
        """Analyse l'historique des scores et génère des visualisations"""

        cache_dir = 'cache/scores'
        if dataset_file and depth_number:
            files = [f'{cache_dir}/{dataset_file}/history_depth_{depth_number}.json']
        else:
            files = glob.glob(f'{cache_dir}/**/history_depth_*.json', recursive=True)

        plt.figure(figsize=(15, 10))

        for file in files:
            with open(file, 'r') as f:
                history = json.load(f)

            valid_scores = [entry['score'] for entry in history['scores'] if entry['is_valid']]

            sns.kdeplot(valid_scores, label=f"{history['dataset']} (Depth {history['depth_number']})")

        plt.title('Score Distribution by Dataset and Depth')
        plt.xlabel('Score')
        plt.ylabel('Density')
        plt.legend()

        # Sauvegarder le graphique
        os.makedirs('cache/visualizations', exist_ok=True)
        plt.savefig('cache/visualizations/score_distribution.png')
        print('📈 Generated visualization: cache/visualizations/score_distribution.png')
        # Vérifie si la meilleure solution trouvée est meilleure que les solutions existantes
        highest_existing_score = Analyser.get_highest_score_from_files(dataset_file)

        best_result = None
        lowest_score = highest_existing_score
        best_score = 0

        for attempt in range(max_attempts):
            solution = Solver.solve(dataset, depth_number, dataset_file)
            score, is_valid, message = test_solution.getSolutionScore(solution, dataset)

            if is_valid and score < lowest_score:
                lowest_score = score

            if is_valid and score > best_score:
                best_score = score
                best_result = solution

            if is_valid and score > highest_existing_score:
                highest_existing_score = score
                print(f'✅ New best score! {best_score} (Previous best: {highest_existing_score})')

                # Supprimer les anciennes solutions avec des scores inférieurs
                pattern = f'.\\solutions\\{dataset_file}_*.json'
                for old_file in glob.glob(pattern):
                    try:
                        old_score = int(old_file.split('_')[2])
                        if old_score < score:
                            os.remove(old_file)
                    except (IndexError, ValueError):
                        continue

                # Sauvegarder la nouvelle meilleure solution
                date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                file_name = f'{dataset_file}_{score}_{date}'

                with open(f'.\\solutions\\{file_name}.json', 'w') as f:
                    f.write(best_result)
                # print('Best solution saved')
            elif not is_valid:
                print(f'❌ Invalid solution: {message}')
            
        print(f'Best score found: {best_score}')

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