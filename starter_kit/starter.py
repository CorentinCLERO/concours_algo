from src.analyser import Analyser
from src.loop import Loop

# dataset_file = "1_example"
# dataset_file = "2_pacman"
# dataset_file = "3_efrei"
# dataset_file = "4_manhattan"
dataset_file = "5_gta"
# dataset_file = "6_paris"
# dataset_file = "7_london"
dataset = open(f'.\\datasets\\{dataset_file}.json').read()
depth_number = 2
max_attempts = 10
print('---------------------------------')
print(f'Solving {dataset_file}')
Loop.loop(dataset, dataset_file, max_attempts, depth_number)

# Analyser un dataset spécifique
# Analyser.analyze_history(max_attempts, dataset, dataset_file)

# Analyser tous les datasets
# Analyser.analyze_history(max_attempts, dataset)