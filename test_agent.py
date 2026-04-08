from agent import Agent
import time


class Search(Agent):
    def __init__(self, player):
        super().__init__(player)
        self.directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        self.we_still_have_skill = True
        self.opponent_still_has_skill = True
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
            "sleep_three": 9000,
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

    def find_all_winning_moves(self, board, player, cells=None):
        if cells is None:
            cells = self.get_candidate_moves(board, player)
        wins = []
        for row, col in cells:
            if board[row][col] != 0:
                continue
            board[row][col] = player
            ok = self.is_win(board, row, col, player)
            board[row][col] = 0
            if ok:
                wins.append((row, col))
        return wins

    def board_has_active_block(self, board):
        size = len(board)
        for i in range(size):
            for j in range(size):
                if board[i][j] not in (0, 1, 2):
                    return True
        return False

    def get_high_pressure_followups(self, board, player, limit=18):
        candidates = self.get_candidate_moves(board, player)
        dangerous = []
        for x, y in candidates[:limit]:
            total_score = self.evaluate_move(board, x, y, player) + self.combo_attack_score(board, x, y, player)
            states = self.get_move_states(board, x, y, player)
            if (
                total_score >= 110000
                or self.combo_attack_score(board, x, y, player) >= 130000
                or states.count("live_three") >= 2
                or ("live_three" in states and "sleep_four" in states)
                or "live_four" in states
            ):
                dangerous.append((total_score, (x, y)))
        dangerous.sort(reverse=True)
        return dangerous

    def get_opponent_pressure(self, board, defender, limit=16):
        attacker = 3 - defender
        pressure = 0
        threat_count = 0
        candidates = self.get_candidate_moves(board, attacker)
        for x, y in candidates[:limit]:
            total_score = self.evaluate_move(board, x, y, attacker) + self.combo_attack_score(board, x, y, attacker)
            if total_score >= 70000:
                threat_count += 1
                pressure += total_score
        return pressure, threat_count

    def get_skill_forced_kill(self, board, attacker, attacker_has_skill):
        if not attacker_has_skill:
            return None, None, -1

        attack_candidates = self.get_candidate_moves(board, attacker)
        best_move = None
        best_block_target = None
        best_score = -1

        for x, y in attack_candidates[:16]:
            if board[x][y] != 0:
                continue

            board[x][y] = attacker
            direct_wins = self.find_all_winning_moves(board, attacker, self.get_candidate_moves(board, attacker))
            pressure_followups = self.get_high_pressure_followups(board, attacker)

            score = -1
            block_target = None

            if len(direct_wins) >= 2:
                score = 950000 + 2000 * len(direct_wins) + self.evaluate_move(board, x, y, attacker)
                block_target = direct_wins[0]
            elif len(direct_wins) == 1:
                fx, fy = direct_wins[0]
                original = board[fx][fy]
                board[fx][fy] = -1
                still_has_direct = len(self.find_all_winning_moves(board, attacker, self.get_candidate_moves(board, attacker))) > 0
                still_has_pressure = len(self.get_high_pressure_followups(board, attacker)) >= 1
                board[fx][fy] = original
                if still_has_direct or still_has_pressure:
                    score = 820000 + self.evaluate_move(board, x, y, attacker)
                    block_target = (fx, fy)
            else:
                if len(pressure_followups) >= 2:
                    fx, fy = pressure_followups[0][1]
                    original = board[fx][fy]
                    board[fx][fy] = -1
                    remain_pressure = self.get_high_pressure_followups(board, attacker)
                    board[fx][fy] = original
                    if len(remain_pressure) >= 1:
                        score = 720000 + pressure_followups[0][0] + self.evaluate_move(board, x, y, attacker)
                        block_target = (fx, fy)
                elif len(pressure_followups) == 1:
                    fx, fy = pressure_followups[0][1]
                    original = board[fx][fy]
                    board[fx][fy] = -1
                    remain_pressure = self.get_high_pressure_followups(board, attacker)
                    board[fx][fy] = original
                    if len(remain_pressure) >= 1 and remain_pressure[0][0] >= 110000:
                        score = 700000 + remain_pressure[0][0] + self.evaluate_move(board, x, y, attacker)
                        block_target = (fx, fy)

            board[x][y] = 0

            if score > best_score:
                best_score = score
                best_move = (x, y)
                best_block_target = block_target

        return best_move, best_block_target, best_score

    def get_multi_threat_defense_move(self, board):
        opp_candidates = self.get_candidate_moves(board, self.opponent)
        threat_list = []
        for x, y in opp_candidates[:18]:
            s = self.evaluate_move(board, x, y, self.opponent) + self.combo_attack_score(board, x, y, self.opponent)
            if s >= 70000:
                threat_list.append((s, (x, y)))
        threat_list.sort(reverse=True)
        if len(threat_list) < 2:
            return None

        defense_candidates = []
        seen = set()
        for _, pos in threat_list[:4]:
            if pos not in seen:
                defense_candidates.append(pos)
                seen.add(pos)
        for pos in self.get_candidate_moves(board, self.player)[:16]:
            if pos not in seen:
                defense_candidates.append(pos)
                seen.add(pos)

        best_move = None
        best_tuple = None
        for x, y in defense_candidates:
            if board[x][y] != 0:
                continue
            board[x][y] = self.player
            pressure, count = self.get_opponent_pressure(board, self.player)
            my_counter = self.evaluate_move(board, x, y, self.player) + self.combo_attack_score(board, x, y, self.player)
            board[x][y] = 0
            score_tuple = (pressure, count, -my_counter)
            if best_tuple is None or score_tuple < best_tuple:
                best_tuple = score_tuple
                best_move = (x, y)
        return best_move

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

    def get_line_string(self, board, row, col, player, dx, dy, span=4):
        chars = []
        size = len(board)
        opponent = 3 - player
        for step in range(-span, span + 1):
            x = row + step * dx
            y = col + step * dy
            if not (0 <= x < size and 0 <= y < size):
                chars.append("2")
            elif step == 0:
                chars.append("1")
            else:
                val = board[x][y]
                if val == player:
                    chars.append("1")
                elif val == 0:
                    chars.append("0")
                elif val == opponent:
                    chars.append("2")
                else:
                    chars.append("2")
        return "".join(chars)

    def line_has_any(self, line, patterns):
        for pattern in patterns:
            if pattern in line:
                return True
        return False

    def classify_line_pattern(self, line):
        if "11111" in line:
            return "five"

        live_four_patterns = ["011110"]
        sleep_four_patterns = [
            "211110", "011112", "01111", "11110", "10111", "11011", "11101",
            "011101", "101110", "110110", "111010", "0101110", "0111010"
        ]
        live_three_patterns = [
            "0011100", "001110", "011100", "010110", "011010", "0101110", "0111010"
        ]
        sleep_three_patterns = [
            "211100", "001112", "211010", "010112", "210110", "011012",
            "2100110", "0110012", "001101", "101100", "0101010", "0010110"
        ]
        live_two_patterns = ["001100", "0010100", "010100", "001010", "010010"]
        sleep_two_patterns = ["211000", "000112", "210100", "001012", "210010", "010012", "0010010"]

        if self.line_has_any(line, live_four_patterns):
            return "live_four"
        if self.line_has_any(line, sleep_four_patterns):
            return "sleep_four"
        if self.line_has_any(line, live_three_patterns):
            return "live_three"
        if self.line_has_any(line, sleep_three_patterns):
            return "sleep_three"
        if self.line_has_any(line, live_two_patterns):
            return "live_two"
        if self.line_has_any(line, sleep_two_patterns):
            return "sleep_two"
        return "other"

    def classify_direction(self, board, row, col, player, dx, dy):
        line = self.get_line_string(board, row, col, player, dx, dy)
        return self.classify_line_pattern(line)

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

        live_three_cnt = states.count("live_three")
        sleep_four_cnt = states.count("sleep_four")
        live_two_cnt = states.count("live_two")
        sleep_three_cnt = states.count("sleep_three")

        if live_three_cnt >= 2:
            score += 100000
        if sleep_four_cnt >= 2:
            score += 90000
        if "live_three" in states and "sleep_four" in states:
            score += 120000
        if "live_four" in states and "sleep_four" in states:
            score += 140000
        if live_two_cnt >= 2:
            score += 2500
        if live_two_cnt >= 3:
            score += 5000
        if sleep_three_cnt >= 2:
            score += 4000

        center = len(board) // 2
        score += max(0, 10 - (abs(row - center) + abs(col - center)))
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
                6 * self.evaluate_move(board, pos[0], pos[1], player)
                + 10 * self.evaluate_move(board, pos[0], pos[1], opponent)
                + 4 * self.combo_attack_score(board, pos[0], pos[1], player)
                + 8 * self.combo_attack_score(board, pos[0], pos[1], opponent)
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
        live_three_points = 0
        sleep_four_points = 0
        live_four_points = 0
        double_three_points = 0
        combo_points = 0

        for x, y in candidate_moves[:12]:
            move_score = self.evaluate_move(board, x, y, player)
            combo_score = self.combo_attack_score(board, x, y, player)
            values.append(move_score + combo_score)
            states = self.get_move_states(board, x, y, player)
            if "live_three" in states:
                live_three_points += 1
            if "sleep_four" in states:
                sleep_four_points += 1
            if "live_four" in states:
                live_four_points += 1
            if states.count("live_three") >= 2:
                double_three_points += 1
            if combo_score >= 130000:
                combo_points += 1

        values.sort(reverse=True)
        if len(values) == 1:
            base = values[0]
        elif len(values) == 2:
            base = values[0] * 5 + values[1] * 3
        elif len(values) == 3:
            base = values[0] * 7 + values[1] * 4 + values[2] * 2
        else:
            base = values[0] * 8 + values[1] * 5 + values[2] * 3 + values[3] * 2

        base += live_three_points * 7000
        base += sleep_four_points * 14000
        base += live_four_points * 26000
        base += double_three_points * 22000
        base += combo_points * 18000
        return base
    def get_forced_tactical_move(self, board):
        opp_skill_kill_move, _, opp_skill_kill_score = self.get_skill_forced_kill(
            board, self.opponent, self.opponent_still_has_skill
        )
        if opp_skill_kill_move is not None and opp_skill_kill_score >= 700000:
            return opp_skill_kill_move, "defense"

        my_skill_kill_move, my_skill_block_target, my_skill_kill_score = self.get_skill_forced_kill(
            board, self.player, self.we_still_have_skill
        )
        if (
            my_skill_kill_move is not None
            and my_skill_block_target is not None
            and my_skill_kill_score >= 700000
        ):
            return (my_skill_kill_move, my_skill_block_target), "skill_attack"

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

        multi_threat_defense = self.get_multi_threat_defense_move(board)
        if multi_threat_defense is not None and opp_best_score >= 80000:
            return multi_threat_defense, "defense"

        if my_best is not None and my_best_score >= 220000:
            return my_best, "attack"
        if opp_best is not None and opp_best_score >= 110000:
            return opp_best, "defense"
        if my_best is not None and opp_best is not None and my_best_score >= opp_best_score + 70000:
            return my_best, "attack"
        if opp_best is not None and my_best is not None and opp_best_score >= my_best_score and opp_best_score >= 100000:
            return opp_best, "defense"
        return None, None

    def evaluate_board(self, board):
        key = self.board_key(board)
        if key in self.eval_cache:
            return self.eval_cache[key]

        my_score = self.evaluate_board_each(self.player, board)
        opp_score = self.evaluate_board_each(self.opponent, board)
        value = my_score - 3.8 * opp_score
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

        my_combo_score = self.get_best_combo_move(board)[1]
        opp_combo_score = self.get_best_opponent_combo_move(board)[1]
        immediate_threat = self.get_immediate_threat_move(board)

        if my_combo_score >= 130000 or opp_combo_score >= 70000 or immediate_threat is not None:
            if empty_count > 95:
                return 4
            if empty_count > 70:
                return 4
            return 5
        if empty_count > 115:
            return 2
        if empty_count > 95:
            return 3
        if empty_count > 75:
            return 3
        if empty_count > 35:
            return 4
        return 5

    def get_search_width(self, depth):
        if depth >= 6:
            return 8
        if depth >= 5:
            return 9
        if depth >= 4:
            return 12
        if depth == 3:
            return 13
        return 13

    def get_immediate_threat_move(self, board):
        oppo_candidates = self.get_candidate_moves(board, self.opponent)
        best_threat = None
        best_threat_score = -1
        for x, y in oppo_candidates[:16]:
            s = self.evaluate_move(board, x, y, self.opponent) + self.combo_attack_score(board, x, y, self.opponent)
            if s > best_threat_score:
                best_threat_score = s
                best_threat = (x, y)
        if best_threat is not None and best_threat_score >= 80000:
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

    def is_tactical_position(self, board):
        if self.get_immediate_threat_move(board) is not None:
            return True
        if self.get_best_combo_move(board)[1] >= 130000:
            return True
        if self.get_best_opponent_combo_move(board)[1] >= 70000:
            return True
        return False

    def alpha_beta(self, board, depth, alpha, beta, player, extended=False):
        if self.time_exceeded():
            raise TimeoutError

        if depth == 0 and not extended and self.is_tactical_position(board):
            depth = 1
            extended = True

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
                score, _ = self.alpha_beta(board, depth - 1, alpha, beta, 3 - player, extended)
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
            score, _ = self.alpha_beta(board, depth - 1, alpha, beta, 3 - player, extended)
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
            board[i][j] = -1
            reduced_pressure, reduced_count = self.get_opponent_pressure(board, self.player)
            board[i][j] = 0
            score += max(0, 220000 - reduced_pressure) + max(0, 3 - reduced_count) * 12000
            if score > best_score:
                best_score = score
                best_move = (i, j)

        board[x][y] = 0

        if best_move is None:
            return None

        if combo_type == "live_four" and best_score >= 8000:
            self.we_still_have_skill = False
            return best_move

        if combo_type == "live_three_sleep_four" and best_score >= 7000:
            self.we_still_have_skill = False
            return best_move

        if combo_type == "double_live_three" and best_score >= 12000:
            self.we_still_have_skill = False
            return best_move

        if combo_type == "sleep_four" and best_score >= 16000:
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
        if self.board_has_active_block(board):
            self.opponent_still_has_skill = False
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
            if forced_type == "skill_attack":
                real_move, skill_target = forced_move
                self.we_still_have_skill = False
                return real_move, skill_target
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
        urgent_defense_move = self.get_multi_threat_defense_move(board)

        if urgent_defense_move is not None and best_oppo_combo_score >= 70000:
            return urgent_defense_move, None
        if best_oppo_combo_move is not None and best_oppo_combo_score >= 70000:
            if best_combo_score < best_oppo_combo_score or best_attack_score < self.pattern_scores["live_four"]:
                return best_oppo_combo_move, None
        if immediate_threat_move is not None:
            opp_threat_score = self.evaluate_move(board, immediate_threat_move[0], immediate_threat_move[1], self.opponent) + self.combo_attack_score(board, immediate_threat_move[0], immediate_threat_move[1], self.opponent)
            if best_combo_score < 120000 and (best_attack_score < self.pattern_scores["live_four"] or opp_threat_score >= best_attack_score):
                return immediate_threat_move, None

        fallback_move = candidate_moves[0]
        if best_attack_move is not None:
            fallback_move = best_attack_move
        if best_combo_move is not None and best_combo_score >= 130000:
            fallback_move = best_combo_move
        if immediate_threat_move is not None and best_combo_score < 120000:
            fallback_move = immediate_threat_move

        stone_count = self.count_stones_on_board(board)
        if urgent_defense_move is not None and best_oppo_combo_score >= 70000:
            move = urgent_defense_move
        elif best_oppo_combo_move is not None and best_oppo_combo_score >= 100000 and best_combo_score < best_oppo_combo_score:
            move = best_oppo_combo_move
        elif immediate_threat_move is not None and best_combo_score < 130000:
            move = immediate_threat_move
        elif best_combo_move is not None and best_combo_score >= 145000:
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
                        if searched_combo_score >= 130000 or self.evaluate_move(board, searched_move[0], searched_move[1], self.player) >= 150000:
                            move = searched_move
                            break
                        move = searched_move
                except TimeoutError:
                    break

        if move is None:
            move = fallback_move
        if move is not None:
            board[move[0]][move[1]] = self.player
            opp_pressure_after_move, opp_pressure_count = self.get_opponent_pressure(board, self.player)
            board[move[0]][move[1]] = 0
            if opp_pressure_count >= 2:
                forced_defense = self.get_multi_threat_defense_move(board)
                if forced_defense is not None:
                    move = forced_defense
        skill_move = self.choose_skill_target(board, move)
        if skill_move is not None:
            return move, skill_move

        return move, None

#python3 gomoku.py -m human
#python3 gomoku.py -m test_agent





