import os
import json
import datetime

class SaveScore:
    def save_score_history(dataset_file, depth_number, score, is_valid, roads_length, timestamp=None):
        """Sauvegarde l'historique des scores dans un fichier JSON"""
        cache_dir = f'cache/scores/{dataset_file}'
        os.makedirs(cache_dir, exist_ok=True)

        history_file = f'{cache_dir}/history_depth_{depth_number}.json'

        # Charger l'historique existant ou créer un nouveau
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except FileNotFoundError:
            history = {
                'dataset': dataset_file,
                'depth_number': depth_number,
                'roads_length': roads_length,
                'scores': [],
                'stats': {
                    'highest_score': 0,
                    'lowest_score': float('inf'),
                    'valid_attempts': 0,
                    'invalid_attempts': 0,
                    'total_attempts': 0
                }
            }

        # Mettre à jour les statistiques
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        score_entry = {
            'score': score,
            'is_valid': is_valid,
            'timestamp': timestamp
        }

        # Limiter le nombre d'entrées en fonction de la taille du dataset
        max_entries = min(1000, max(100, int(roads_length / depth_number)))
        history['scores'].append(score_entry)
        if len(history['scores']) > max_entries:
            history['scores'] = history['scores'][-max_entries:]

        # Mettre à jour les stats
        stats = history['stats']
        stats['total_attempts'] += 1
        if is_valid:
            stats['valid_attempts'] += 1
            stats['highest_score'] = max(stats['highest_score'], score)
            stats['lowest_score'] = min(stats['lowest_score'], score)
        else:
            stats['invalid_attempts'] += 1

        # Sauvegarder l'historique
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

        return history
