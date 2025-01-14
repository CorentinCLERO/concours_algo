import os
import glob
import json
import test_solution
import datetime
from src.analyser import Analyser
from src.solver import Solver
from src.save_score import SaveScore

class Loop:
  def loop(dataset, dataset_file, max_attempts, depth_number):
    # Charger le dataset et obtenir le nombre de routes
    dataset_data = json.loads(dataset)
    roads_length = len(dataset_data['roads'])
    print(f"Dataset {dataset_file} contains {roads_length} roads")

    highest_existing_score = Analyser.get_highest_score_from_files(dataset_file)
    best_result = None
    best_score = 0

    for attempt in range(max_attempts):
        print(f"\nAttempt {attempt + 1}/{max_attempts}")
        solution = Solver.solve(dataset, depth_number, dataset_file)
        score, is_valid, message = test_solution.getSolutionScore(solution, dataset)

        # Sauvegarder dans l'historique
        history = SaveScore.save_score_history(dataset_file, depth_number, score, is_valid, roads_length)

        if is_valid and score > best_score:
            best_score = score
            best_result = solution

            if score > highest_existing_score:
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

        elif not is_valid:
            print(f'❌ Invalid solution: {message}')

        # Afficher les stats périodiquement
        if (attempt + 1) % 10 == 0:
            stats = history['stats']
            print(f"\n📊 Current Statistics (Depth {depth_number}):")
            print(f"Highest Score: {stats['highest_score']}")
            print(f"Lowest Valid Score: {stats['lowest_score']}")
            print(f"Valid/Total Attempts: {stats['valid_attempts']}/{stats['total_attempts']}")

    print(f'\n🏁 Final best score: {best_score} highest existing score : {highest_existing_score}')
    return best_score
