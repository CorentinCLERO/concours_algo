import datetime
import networkx as nx
import random
from src.solver.path_evaluator import PathEvaluator

class DaySimulator:
    """Classe responsable de la simulation d'une journée complète"""

    def __init__(self, G, dataset, base_id, depth_complexity, dist_to_base):
        """Initialise le simulateur avec les paramètres nécessaires"""
        self.G = G
        self.dataset = dataset
        self.base_id = base_id
        self.depth_complexity = depth_complexity
        self.dist_to_base = dist_to_base
        self.time = datetime.datetime.now().isoformat()

    def simulate_day(self, day_i, curr_node, battery_remaining, visited_roads, path, score, best_daily_scores, is_last_day=False):
        """
        Simule une journée complète de déplacements avec plusieurs essais si nécessaire

        Args:
            day_i: Index du jour actuel
            curr_node: Nœud actuel
            battery_remaining: Batterie restante
            visited_roads: Routes déjà visitées
            path: Chemin parcouru
            score: Score actuel
            best_daily_scores: Liste des meilleurs scores journaliers
            is_last_day: Indique si c'est le dernier jour

        Returns:
            tuple: (curr_node, battery_remaining, visited_roads, path, score, found_better_score)
        """
        max_tries = 3
        current_try = 0
        best_day_result = None
        best_day_score = float('-inf')
        initial_state = (curr_node, battery_remaining, visited_roads.copy(), path.copy(), score)

        # Calcul du score cumulé attendu pour ce jour
        expected_cumulative_score = best_daily_scores[day_i] if best_daily_scores and day_i < len(best_daily_scores) else 0
        if day_i > 0 and best_daily_scores:
            expected_cumulative_score += best_daily_scores[day_i - 1]

        while current_try < max_tries:
            failed_attempts = 0
            curr_node, battery_remaining, visited_roads, path, score = initial_state
            day_start_score = score

            while True:
                try:
                    # Gestion des échecs répétés
                    if failed_attempts >= 3:
                        if not is_last_day:
                            curr_node, battery_remaining, visited_roads, path, score = self._handle_failed_attempts(
                                curr_node, battery_remaining, visited_roads, path, score)
                        break

                    # Choix du prochain nœud
                    next_node = self._choose_next_node(curr_node, battery_remaining, visited_roads, is_last_day)
                    if next_node is None:
                        if not is_last_day:
                            next_node = self.base_id
                        else:
                            break

                    # Validation et mise à jour
                    if not self._validate_move(curr_node, next_node):
                        failed_attempts += 1
                        continue

                    # Mise à jour de l'état
                    curr_node, battery_remaining, visited_roads, path, score = self._update_state(
                        curr_node, next_node, battery_remaining, visited_roads, path, score, best_daily_scores[day_i])

                    # Vérification de fin de journée
                    if self._should_end_day(curr_node, battery_remaining, is_last_day):
                        break

                except Exception as e:
                    print(f"Error during day simulation: {e}")
                    failed_attempts += 1
                    if failed_attempts >= 3:
                        break

            # Calcul du score de la journée
            day_score = score - day_start_score

            # Mise à jour du meilleur résultat si nécessaire
            if day_score > best_day_score:
                best_day_score = day_score
                best_day_result = (curr_node, battery_remaining, visited_roads.copy(), path.copy(), score)

            # Vérification si le score est meilleur que le meilleur score connu
            if best_daily_scores and day_i < len(best_daily_scores):
                if score > best_daily_scores[day_i] * 0.9:
                    if score > best_daily_scores[day_i]:
                        print(f"👏 Found better score on try {current_try + 1}: {score} > {best_daily_scores[day_i]}, hope it's the one !")
                    else:
                        print(f"🙏 Found a good score on try {current_try + 1}: {score} > {best_daily_scores[day_i]}")
                    return (*best_day_result, True)
            else:
                # Si pas de score de référence, on considère que c'est un succès
                return (*best_day_result, True)

            current_try += 1
            if current_try < max_tries:
                print(f"Score not better ({score} <= {best_daily_scores[day_i]}), trying again ({current_try + 1}/{max_tries})")

        # Si aucun meilleur score n'a été trouvé après tous les essais
        print(f"No better score found after {max_tries} tries. Best: {best_day_score + score}")
        return (*best_day_result, False)

    def _handle_failed_attempts(self, curr_node, battery_remaining, visited_roads, path, score):
        """Gère le retour à la base en cas d'échecs répétés"""
        print(f"Too many failed attempts, forcing return to base")
        try:
            shortest_path = nx.shortest_path(self.G, curr_node, self.base_id, weight='length')
            for node in shortest_path[1:]:
                path.append(node)
                if (curr_node, node) not in visited_roads:
                    score += self.G[curr_node][node]['length']
                visited_roads.add((curr_node, node))
                visited_roads.add((node, curr_node))
                curr_node = node
        except nx.NetworkXNoPath:
            print(f"No path to base found, teleporting to base")
            path.append(self.base_id)
            curr_node = self.base_id
        return curr_node, battery_remaining, visited_roads, path, score

    def _choose_next_node(self, curr_node, battery_remaining, visited_roads, is_last_day):
        """
        Choisit le prochain nœud à visiter

        Returns:
            int: ID du prochain nœud ou None si aucun nœud valide n'est trouvé
        """
        neighbors = list(self.G.neighbors(curr_node))
        if not neighbors:
            return None

        random.shuffle(neighbors)
        best_path, _ = PathEvaluator.find_best_path(
            self.G, curr_node, battery_remaining, visited_roads,
            self.dist_to_base, self.dataset, depth=0,
            max_depth=self.depth_complexity, base_id=self.base_id,
            is_last_day=is_last_day
        )

        return best_path[1] if best_path and len(best_path) > 1 else None

    def _validate_move(self, curr_node, next_node):
        """
        Valide si le mouvement vers le prochain nœud est possible

        Returns:
            bool: True si le mouvement est valide, False sinon
        """
        if not self.G.has_edge(curr_node, next_node):
            print(f"Warning: Invalid edge {curr_node}->{next_node}, returning to base")
            return False
        return True

    def _update_state(self, curr_node, next_node, battery_remaining, visited_roads, path, score, best_daily_score):
        """
        Met à jour l'état après un mouvement

        Returns:
            tuple: (new_curr_node, new_battery, visited_roads, path, score)
        """
        # Mise à jour du score pour les nouvelles routes
        if (curr_node, next_node) not in visited_roads:
            score += self.G[curr_node][next_node]['length']
            self._print_progress(score, best_daily_score)

        # Marquage des routes comme visitées
        visited_roads.add((curr_node, next_node))
        visited_roads.add((next_node, curr_node))

        # Mise à jour de la batterie et de la position
        battery_remaining -= self.G[curr_node][next_node]['length']
        path.append(next_node)

        return next_node, battery_remaining, visited_roads, path, score

    def _should_end_day(self, curr_node, battery_remaining, is_last_day):
        """
        Détermine si la journée doit se terminer
        """
        # Si ce n'est pas le dernier jour et qu'on est à la base, on termine
        if not is_last_day and curr_node == self.base_id:
            return True

        # Pour le dernier jour
        if is_last_day:
            # Ne jamais terminer au base_id le dernier jour
            if curr_node == self.base_id:
                return False

            # Vérifier s'il reste des mouvements possibles
            has_feasible_moves = False
            for n in self.G.neighbors(curr_node):
                if (self.G.has_edge(curr_node, n) and
                    battery_remaining >= self.G[curr_node][n]['length'] and
                    n != self.base_id):  # Ignorer les mouvements vers la base
                    has_feasible_moves = True
                    break

            # Terminer seulement si aucun mouvement n'est possible
            if not has_feasible_moves:
                print(f"No more feasible non-base moves with remaining battery: {battery_remaining}")
                return True

        return False

    def _print_progress(self, score, best_daily_score):
        """Affiche la progression si nécessaire"""
        current_time = datetime.datetime.now()
        if current_time - datetime.datetime.fromisoformat(self.time) > datetime.timedelta(seconds=5):
            print(f"😴 It's been a while so the current score: {score}/{best_daily_score}")
            self.time = current_time.isoformat()