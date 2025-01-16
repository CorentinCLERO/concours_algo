from src.analyser import Analyser
from src.loop import Loop
import time

# dataset_file = "1_example"
# dataset_file = "2_pacman"
# dataset_file = "3_efrei"
# dataset_file = "4_manhattan"
# dataset_file = "5_gta"
dataset_file = "6_paris"
# dataset_file = "7_london"
dataset = open(f'.\\datasets\\{dataset_file}.json').read()
depth_number = 2
max_attempts = 100
print('---------------------------------')
print(f'Solving {dataset_file}')
start_time = time.time()
Loop.loop(dataset, dataset_file, max_attempts, depth_number)
end_time = time.time()
elapsed_time = end_time - start_time
print(f"Execution time: {elapsed_time:.2f} seconds")

# Analyser un dataset spécifique
# Analyser.analyze_history(max_attempts, dataset, dataset_file)

# Analyser tous les datasets
# Analyser.analyze_history(max_attempts, dataset)

# 6sec