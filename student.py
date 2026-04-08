from agent import Agent
import time


class Search(Agent):
    def __init__(self, player):
        super().__init__(player)
        self.directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        self.we_still_have_skill = True
        self.search_time_limit = 56.0
        self.start_time = 0.0
        self.eval_cache = {}
        self.candidate_cache = {}
        self.move_eval_cache = {}
        self.move_state_cache = {}
        self.combo_score_cache = {}
        self.pattern_scores = {
            "five": 1000000,
            "live_four": 120000,
            "sleep_four": 45000,
            "live_three": 12000,
            "sleep_three": 3000,
            "live_two": 800,
            "sleep_two": 120,
            "other": 0,
        }
    def board_key(self, board):
        return tuple(tuple(int(x) for x in row) for row in board)

    def time_exceeded(self):
        return time.time() - self.start_time >= self.search_time_limit

    def find_winning_move(self, board, player, cells):
        for row, col in cells:
            board[row][col] = player
            ok = self.is_win(board, row, col, player)
            board[row][col] = 0
            if ok:
                return row, col
        return None

    def is_win(self, board, row, col, player):
        for dx, dy in self.directions:
            count = 1
            count += self.count_stones(board, row, col, player, dx, dy)
            count += self.count_stones(board, row, col, player, -dx, -dy)
            if count >= 5:
                return True
        return False

    def count_stones(self, board, row, col, player, dx, dy):
        x, y = row + dx, col + dy
        count = 0
        size = len(board)
        while 0 <= x < size and 0 <= y < size and board[x][y] == player:
            count += 1
            x += dx
            y += dy
        return count

    def classify_direction(self, board, row, col, player, dx, dy):
        count1 = self.count_stones(board, row, col, player, dx, dy)
        count2 = self.count_stones(board, row, col, player, -dx, -dy)
        total = count1 + count2 + 1

        size = len(board)
        x1, y1 = row + dx * (count1 + 1), col + dy * (count1 + 1)
        x2, y2 = row - dx * (count2 + 1), col - dy * (count2 + 1)

        open_ends = 0
        if 0 <= x1 < size and 0 <= y1 < size and board[x1][y1] == 0:
            open_ends += 1
        if 0 <= x2 < size and 0 <= y2 < size and board[x2][y2] == 0:
            open_ends += 1

        if total >= 5:
            return "five"
        if total == 4 and open_ends == 2:
            return "live_four"
        if total == 4 and open_ends == 1:
            return "sleep_four"
        if total == 3 and open_ends == 2:
            return "live_three"
        if total == 3 and open_ends == 1:
            return "sleep_three"
        if total == 2 and open_ends == 2:
            return "live_two"
        if total == 2 and open_ends == 1:
            return "sleep_two"
        return "other"

    def evaluate_move(self, board, row, col, player):
        key = (self.board_key(board), row, col, player)
        if key in self.move_eval_cache:
            return self.move_eval_cache[key]

        if board[row][col] != 0:
            self.move_eval_cache[key] = -10**9
            return -10**9

        score = 0
        states = self.get_move_states(board, row, col, player)
        for state in states:
            score += self.pattern_scores[state]

        if states.count("live_three") >= 2:
            score += 80000
        if states.count("sleep_four") >= 2:
            score += 70000
        if "live_three" in states and "sleep_four" in states:
            score += 90000
        if states.count("live_two") >= 2:
            score += 1500
        if states.count("live_two") >= 3:
            score += 3000

        center = len(board) // 2
        score += max(0, 8 - (abs(row - center) + abs(col - center)))
        self.move_eval_cache[key] = score
        return score

    def get_move_states(self, board, row, col, player):
        key = (self.board_key(board), row, col, player)
        if key in self.move_state_cache:
            return self.move_state_cache[key]

        states = []
        for dx, dy in self.directions:
            states.append(self.classify_direction(board, row, col, player, dx, dy))
        self.move_state_cache[key] = states
        return states

    def is_combo_attack_move(self, board, row, col, player):
        states = self.get_move_states(board, row, col, player)
        if "live_four" in states:
            return True
        if "sleep_four" in states:
            return True
        if states.count("live_three") >= 2:
            return True
        if "live_three" in states and "sleep_four" in states:
            return True
        return False

    def get_strict_combo_type(self, board, row, col, player):
        states = self.get_move_states(board, row, col, player)
        if "live_four" in states:
            return "live_four"
        if "sleep_four" in states and "live_three" in states:
            return "live_three_sleep_four"
        if states.count("live_three") >= 2:
            return "double_live_three"
        if "sleep_four" in states:
            return "sleep_four"
        return None

    def combo_skill_target_score(self, board, row, col):
        opp_attack_score = self.evaluate_move(board, row, col, self.opponent)
        my_blocked_score = self.evaluate_move(board, row, col, self.player)
        opp_combo_score = self.combo_attack_score(board, row, col, self.opponent)
        return 5 * my_blocked_score + 2 * opp_attack_score + 2 * opp_combo_score

    def combo_attack_score(self, board, row, col, player):
        key = (self.board_key(board), row, col, player)
        if key in self.combo_score_cache:
            return self.combo_score_cache[key]

        combo_type = self.get_strict_combo_type(board, row, col, player)
        score = 0
        if combo_type == "live_four":
            score = 220000
        elif combo_type == "live_three_sleep_four":
            score = 200000
        elif combo_type == "double_live_three":
            score = 170000
        elif combo_type == "sleep_four":
            score = 130000

        self.combo_score_cache[key] = score
        return score

    def get_best_combo_move(self, board):
        my_candidates = self.get_candidate_moves(board, self.player)
        best_move = None
        best_score = -1
        for x, y in my_candidates[:12]:
            s = self.combo_attack_score(board, x, y, self.player)
            if s > best_score:
                best_score = s
                best_move = (x, y)
        return best_move, best_score

    def get_best_opponent_combo_move(self, board):
        oppo_candidates = self.get_candidate_moves(board, self.opponent)
        best_move = None
        best_score = -1
        for x, y in oppo_candidates[:12]:
            s = self.combo_attack_score(board, x, y, self.opponent)
            if s > best_score:
                best_score = s
                best_move = (x, y)
        return best_move, best_score

    def get_candidate_moves(self, board, player):
        key = (self.board_key(board), player)
        if key in self.candidate_cache:
            return self.candidate_cache[key]

        size = len(board)
        center = size // 2
        opponent = 3 - player

        stone_cells = []
        empty_cells = []
        for i in range(size):
            for j in range(size):
                if board[i][j] == 0:
                    empty_cells.append((i, j))
                elif board[i][j] == 1 or board[i][j] == 2:
                    stone_cells.append((i, j))

        if not empty_cells:
            self.candidate_cache[key] = []
            return []
        if not stone_cells:
            self.candidate_cache[key] = [(center, center)]
            return [(center, center)]

        candidate_set = set()
        radius = 2
        for x, y in stone_cells:
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < size and 0 <= ny < size and board[nx][ny] == 0:
                        candidate_set.add((nx, ny))

        if not candidate_set:
            candidate_set = set(empty_cells)

        candidate_moves = list(candidate_set)
        candidate_moves.sort(
            key=lambda pos: (
                8 * self.evaluate_move(board, pos[0], pos[1], player)
                + 7 * self.evaluate_move(board, pos[0], pos[1], opponent)
                + 5 * self.combo_attack_score(board, pos[0], pos[1], player)
                + 2 * self.combo_attack_score(board, pos[0], pos[1], opponent)
            ),
            reverse=True,
        )
        self.candidate_cache[key] = candidate_moves
        return candidate_moves

    def evaluate_board_each(self, player, board):
        candidate_moves = self.get_candidate_moves(board, player)
        if not candidate_moves:
            return 0
        values = []
        for x, y in candidate_moves[:10]:
            v = self.evaluate_move(board, x, y, player) + self.combo_attack_score(board, x, y, player)
            values.append(v)
        values.sort(reverse=True)
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return values[0] * 5 + values[1] * 3
        if len(values) == 3:
            return values[0] * 7 + values[1] * 4 + values[2] * 2
        return values[0] * 8 + values[1] * 5 + values[2] * 3 + values[3] * 2
    def get_forced_tactical_move(self, board):
        my_candidates = self.get_candidate_moves(board, self.player)
        opp_candidates = self.get_candidate_moves(board, self.opponent)

        my_best = None
        my_best_score = -1
        for x, y in my_candidates[:12]:
            s = self.evaluate_move(board, x, y, self.player) + self.combo_attack_score(board, x, y, self.player)
            if s > my_best_score:
                my_best_score = s
                my_best = (x, y)

        opp_best = None
        opp_best_score = -1
        for x, y in opp_candidates[:12]:
            s = self.evaluate_move(board, x, y, self.opponent) + self.combo_attack_score(board, x, y, self.opponent)
            if s > opp_best_score:
                opp_best_score = s
                opp_best = (x, y)

        if my_best is not None and my_best_score >= 220000:
            return my_best, "attack"
        if opp_best is not None and opp_best_score >= 180000:
            return opp_best, "defense"
        if my_best is not None and opp_best is not None and my_best_score >= opp_best_score + 50000:
            return my_best, "attack"
        if opp_best is not None and my_best is not None and opp_best_score > my_best_score and opp_best_score >= 120000:
            return opp_best, "defense"
        return None, None

    def evaluate_board(self, board):
        key = self.board_key(board)
        if key in self.eval_cache:
            return self.eval_cache[key]

        my_score = self.evaluate_board_each(self.player, board)
        opp_score = self.evaluate_board_each(self.opponent, board)
        value = my_score - 2.5 * opp_score
        self.eval_cache[key] = value
        return value

    def is_board_full(self, board):
        size = len(board)
        for i in range(size):
            for j in range(size):
                if board[i][j] == 0:
                    return False
        return True

    def choose_depth(self, board):
        empty_count = 0
        size = len(board)
        for i in range(size):
            for j in range(size):
                if board[i][j] == 0:
                    empty_count += 1
        if empty_count > 115:
            return 2
        if empty_count > 95:
            return 3
        if empty_count > 80:
            return 4
        if empty_count > 35:
            return 5
        return 5

    def get_search_width(self, depth):
        if depth >= 5:
            return 6
        if depth >= 4:
            return 8
        if depth == 3:
            return 11
        return 14

    def get_immediate_threat_move(self, board):
        oppo_candidates = self.get_candidate_moves(board, self.opponent)
        best_threat = None
        best_threat_score = -1
        for x, y in oppo_candidates:
            s = self.evaluate_move(board, x, y, self.opponent)
            if s > best_threat_score:
                best_threat_score = s
                best_threat = (x, y)
        if best_threat is not None and best_threat_score >= self.pattern_scores["live_three"]:
            return best_threat
        return None

    def get_best_attack_move(self, board):
        my_candidates = self.get_candidate_moves(board, self.player)
        if not my_candidates:
            return None, -1
        best_move = None
        best_score = -1
        for x, y in my_candidates[:12]:
            s = self.evaluate_move(board, x, y, self.player)
            if s > best_score:
                best_score = s
                best_move = (x, y)
        return best_move, best_score

    def count_stones_on_board(self, board):
        size = len(board)
        cnt = 0
        for i in range(size):
            for j in range(size):
                if board[i][j] == 1 or board[i][j] == 2:
                    cnt += 1
        return cnt

    def alpha_beta(self, board, depth, alpha, beta, player):
        if self.time_exceeded():
            raise TimeoutError

        candidate_moves = self.get_candidate_moves(board, player)
        candidate_moves = candidate_moves[: self.get_search_width(depth)]

        if depth == 0 or not candidate_moves or self.is_board_full(board):
            return self.evaluate_board(board), None

        winning_move = self.find_winning_move(board, player, candidate_moves)
        if winning_move is not None:
            if player == self.player:
                return 10**9, winning_move
            return -10**9, winning_move

        maximizing = player == self.player
        best_move = candidate_moves[0]

        if maximizing:
            best_score = float("-inf")
            for x, y in candidate_moves:
                if self.time_exceeded():
                    raise TimeoutError
                board[x][y] = player
                score, _ = self.alpha_beta(board, depth - 1, alpha, beta, 3 - player)
                board[x][y] = 0
                if score > best_score:
                    best_score = score
                    best_move = (x, y)
                alpha = max(alpha, best_score)
                if alpha >= beta:
                    break
            return best_score, best_move

        best_score = float("inf")
        for x, y in candidate_moves:
            if self.time_exceeded():
                raise TimeoutError
            board[x][y] = player
            score, _ = self.alpha_beta(board, depth - 1, alpha, beta, 3 - player)
            board[x][y] = 0
            if score < best_score:
                best_score = score
                best_move = (x, y)
            beta = min(beta, best_score)
            if alpha >= beta:
                break
        return best_score, best_move

    def choose_skill_target(self, board, my_move):
        if not self.we_still_have_skill:
            return None

        x, y = my_move
        board[x][y] = self.player

        combo_type = self.get_strict_combo_type(board, x, y, self.player)
        if combo_type is None:
            board[x][y] = 0
            return None

        oppo_candidates = self.get_candidate_moves(board, self.opponent)
        best_move = None
        best_score = -1
        for i, j in oppo_candidates:
            score = self.combo_skill_target_score(board, i, j)
            if score > best_score:
                best_score = score
                best_move = (i, j)

        board[x][y] = 0

        if best_move is None:
            return None


        if combo_type == "live_four" and best_score >= 12000:
            self.we_still_have_skill = False
            return best_move

        if combo_type == "live_three_sleep_four" and best_score >= 10000:
            self.we_still_have_skill = False
            return best_move

        if combo_type == "double_live_three" and best_score >= 18000:
            self.we_still_have_skill = False
            return best_move

        if combo_type == "sleep_four" and best_score >= 22000:
            self.we_still_have_skill = False
            return best_move

        return None

    def make_move(self, board):
        self.start_time = time.time()
        self.eval_cache = {}
        self.candidate_cache = {}
        self.move_eval_cache = {}
        self.move_state_cache = {}
        self.combo_score_cache = {}
        candidate_moves = self.get_candidate_moves(board, self.player)
        if not candidate_moves:
            return None, None

        self_winning_move = self.find_winning_move(board, self.player, candidate_moves)
        if self_winning_move is not None:
            return self_winning_move, None

        oppo_winning_move = self.find_winning_move(board, self.opponent, candidate_moves)
        if oppo_winning_move is not None:
            return oppo_winning_move, None

        forced_move, forced_type = self.get_forced_tactical_move(board)
        if forced_move is not None:
            if forced_type == "attack":
                strict_combo_type = self.get_strict_combo_type(board, forced_move[0], forced_move[1], self.player)
                if strict_combo_type is not None:
                    skill_move = self.choose_skill_target(board, forced_move)
                    if skill_move is not None:
                        return forced_move, skill_move
                return forced_move, None
            return forced_move, None

        immediate_threat_move = self.get_immediate_threat_move(board)
        best_attack_move, best_attack_score = self.get_best_attack_move(board)
        best_combo_move, best_combo_score = self.get_best_combo_move(board)
        best_oppo_combo_move, best_oppo_combo_score = self.get_best_opponent_combo_move(board)
        if best_oppo_combo_move is not None and best_oppo_combo_score >= 80000:
            if best_combo_score < best_oppo_combo_score and best_attack_score < self.pattern_scores["live_four"]:
                return best_oppo_combo_move, None
        if immediate_threat_move is not None:
            opp_threat_score = self.evaluate_move(board, immediate_threat_move[0], immediate_threat_move[1], self.opponent)
            if best_combo_score < 80000 and (best_attack_score < self.pattern_scores["sleep_four"] or opp_threat_score >= best_attack_score):
                return immediate_threat_move, None

        fallback_move = candidate_moves[0]
        if best_attack_move is not None:
            fallback_move = best_attack_move
        if best_combo_move is not None and best_combo_score >= 130000:
            fallback_move = best_combo_move
        if immediate_threat_move is not None and best_combo_score < 80000:
            fallback_move = immediate_threat_move

        stone_count = self.count_stones_on_board(board)
        if best_oppo_combo_move is not None and best_oppo_combo_score >= 140000 and best_combo_score < best_oppo_combo_score:
            move = best_oppo_combo_move
        elif best_combo_move is not None and best_combo_score >= 130000:
            move = best_combo_move
        elif best_attack_move is not None and best_attack_score >= self.pattern_scores["live_three"]:
            move = best_attack_move
        elif stone_count <= 2 and best_attack_move is not None:
            move = best_attack_move
        else:
            target_depth = self.choose_depth(board)
            move = fallback_move
            for current_depth in range(1, target_depth + 1):
                try:
                    _, searched_move = self.alpha_beta(board, current_depth, float("-inf"), float("inf"), self.player)
                    if searched_move is not None:
                        searched_combo_score = self.combo_attack_score(board, searched_move[0], searched_move[1], self.player)
                        if searched_combo_score >= 130000:
                            move = searched_move
                            break
                        move = searched_move
                except TimeoutError:
                    break

        if move is None:
            move = fallback_move
        skill_move = self.choose_skill_target(board, move)
        if skill_move is not None:
            return move, skill_move

        return move, None
