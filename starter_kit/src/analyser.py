import os
import glob
import json
import test_solution
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from src.solver.solver import Solver

class Analyser:
    @staticmethod
    def analyze_history(max_attempts, dataset, dataset_file=None):
        """Analyse l'historique des scores et génère des visualisations"""

        cache_dir = 'cache/scores'
        if dataset_file:
            files = [f'{cache_dir}/{dataset_file}/history_depth_*.json']
        else:
            files = glob.glob(f'{cache_dir}/**/history_depth_*.json', recursive=True)

        plt.figure(figsize=(12, 8))

        # Style du graphique
        plt.style.use('seaborn-v0_8-darkgrid')

        # Palette de couleurs unique pour chaque profondeur
        depths = []
        data_by_depth = {}

        # Charger les données et organiser par profondeur
        for file in files:
            with open(file, 'r') as f:
                history = json.load(f)

            depth = history['depth_number']
            depths.append(depth)

            scores_data = [(entry['score'], entry['timestamp'])
                           for entry in history['scores']
                           if entry['is_valid']]
            scores_data.sort(key=lambda x: x[1])  # Tri par timestamp

            if depth not in data_by_depth:
                data_by_depth[depth] = {'scores': [], 'timestamps': []}

            data_by_depth[depth]['scores'].extend([score for score, _ in scores_data])
            data_by_depth[depth]['timestamps'].extend(
                [datetime.datetime.strptime(ts, "%Y%m%d_%H%M%S") for _, ts in scores_data]
            )

        # Générer une palette de couleurs unique
        unique_depths = sorted(set(depths))
        colors = sns.color_palette("tab10", len(unique_depths))
        depth_color_map = {depth: colors[i] for i, depth in enumerate(unique_depths)}

        # Tracer les courbes
        for depth, data in data_by_depth.items():
            scores = data['scores']
            timestamps = data['timestamps']

            # Calcul de la moyenne mobile
            moving_avg = pd.Series(scores).rolling(window=10).mean()

            # Tracer les points et la courbe
            plt.scatter(timestamps, scores, alpha=0.5, color=depth_color_map[depth], label=f"Depth {depth}")
            plt.plot(timestamps, moving_avg, '-', linewidth=2, color=depth_color_map[depth])

        # Personnalisation du graphique
        plt.title('Évolution des Scores par Profondeur de Recherche', fontsize=16, pad=20)
        plt.xlabel('Temps', fontsize=14)
        plt.ylabel('Score', fontsize=14)
        plt.grid(True, alpha=0.3)

        # Rotation des labels de l'axe x
        plt.xticks(rotation=45)

        # Légende simplifiée
        plt.legend(title="Profondeur", fontsize=12, title_fontsize=14)

        # Ajustement automatique de la mise en page
        plt.tight_layout()

        # Sauvegarder le graphique
        os.makedirs('cache/visualizations', exist_ok=True)
        plt.savefig('cache/visualizations/score_evolution_cleaned.png', bbox_inches='tight', dpi=300)
        print('📈 Generated visualization: cache/visualizations/score_evolution_cleaned.png')

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