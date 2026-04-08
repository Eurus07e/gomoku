from agent import Agent


class Search(Agent):
    def __init__(self, player):
        super().__init__(player)
        # TODO: 在这里添加任何你需要的初始化代码
        self.directions = [
        (0, 1),
        (1, 0),
        (1, 1),
        (1, -1),
        ]



    def find_winning_move(self, board, player, empty_cells):
        for row, col in empty_cells:
            board[row][col] = player
            if self.is_win(board, row, col, player):
                board[row][col] = 0
                return row, col
            board[row][col] = 0
        return None

    def is_win(self,board, row, col, player):
        for dx, dy in self.directions:
            count = 1
            count += self.count_stones(board, row, col, player, dx, dy)
            count += self.count_stones(board, row, col, player, -dx, -dy)
            if count >= 5:
                return True
        return False

    def count_stones(self, board, row, col, player, dx, dy):
        x, y = row +dx , col + dy
        count = 0
        while 0 <= x < len(board) and 0 <= y < len(board) and board[x][y] == player:
            count += 1
            x += dx
            y += dy
        return count

    def evaluate_move(self, board, row, col, player):
        scores = {
            "five": 100000,
            "live_four": 10000,
            "sleep_four": 4000,
            "live_three": 1000,
            "sleep_three": 200,
            "live_two": 50,
            "other": 0,
        }

        score = 0
        states = []
        for dx, dy in self.directions:
            state = self.classify_direction(board, row, col, player, dx, dy)
            states.append(state)
            score += scores[state]
        if states.count("live_three") >=2:
            score +=5000
        if "live_three" in states and "sleep_four" in states:
            score += 8000
        if states.count("sleep_four") >= 2:
            score += 15000
        if row ==len(board)//2 and col ==len(board)//2:
            score +=5
        return score

    def classify_direction(self, board, row, col, player, dx, dy):
        count1 = self.count_stones(board, row, col, player, dx, dy)
        count2 = self.count_stones(board, row, col, player, -dx, -dy)

        total = count1 + count2 + 1

        x1, y1 = row + dx * (count1 + 1), col + dy * (count1 + 1)
        x2, y2 = row - dx * (count2 + 1), col - dy * (count2 + 1)

        open_ends = 0
        if 0 <= x1 < len(board) and 0 <= y1 < len(board) and board[x1][y1] == 0:
            open_ends += 1
        if 0 <= x2 < len(board) and 0 <= y2 < len(board) and board[x2][y2] == 0:
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
        return "other"

    def get_candidate_moves(self, board):
        size = len(board)
        center = size // 2

        stone_cells = []
        empty_cells = []
        for i in range(size):
            for j in range(size):
                if board[i][j] == 0:
                    empty_cells.append((i, j))
                elif board[i][j] == 1 or board[i][j] == 2:
                    stone_cells.append((i, j))

        if not empty_cells:
            return []

        if not stone_cells:
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
            return empty_cells

        candidate_moves = list(candidate_set)
        candidate_moves.sort(
            key=lambda pos: 5 * self.evaluate_move(board, pos[0], pos[1], self.player)
            + 2 * self.evaluate_move(board, pos[0], pos[1], self.opponent),
            reverse=True,
        )
        return candidate_moves

    def is_board_full(self, board):
        for i in range(len(board)):
            for j in range(len(board)):
                if board[i][j] == 0:
                    return False
        return True

    def choose_search_depth(self, board):
        empty_count = 0
        for i in range(len(board)):
            for j in range(len(board)):
                if board[i][j] == 0:
                    empty_count += 1

        if empty_count > 70:
            return 4
        if empty_count > 40:
            return 5
        if empty_count > 20:
            return 6
        return 7

    def alphabeta(self, board, depth, alpha, beta, maximizing_player, current_player):
        candidate_moves = self.get_candidate_moves(board)
        if depth >= 4:
            candidate_moves = candidate_moves[:70]
        elif depth >= 3:
            candidate_moves = candidate_moves[:100]

        if depth == 0 or not candidate_moves or self.is_board_full(board):
            return self.evaluate_board(self.player, board), None

        winning_move = self.find_winning_move(board, current_player, candidate_moves)
        if winning_move is not None:
            if current_player == self.player:
                return 10**9, winning_move
            return -10**9, winning_move

        if maximizing_player:
            best_value = float("-inf")
            best_move = candidate_moves[0]

            for row, col in candidate_moves:
                board[row][col] = current_player
                value, _ = self.alphabeta(
                    board,
                    depth - 1,
                    alpha,
                    beta,
                    False,
                    3 - current_player,
                )
                board[row][col] = 0

                if value > best_value:
                    best_value = value
                    best_move = (row, col)

                alpha = max(alpha, best_value)
                if alpha >= beta:
                    break

            return best_value, best_move

        best_value = float("inf")
        best_move = candidate_moves[0]

        for row, col in candidate_moves:
            board[row][col] = current_player
            value, _ = self.alphabeta(
                board,
                depth - 1,
                alpha,
                beta,
                True,
                3 - current_player,
            )
            board[row][col] = 0

            if value < best_value:
                best_value = value
                best_move = (row, col)

            beta = min(beta, best_value)
            if alpha >= beta:
                break

        return best_value, best_move

    def evaluate_board_each(self, player, board):
        score = 0
        empty_cells = [
            (i, j)
            for i in range(len(board))
            for j in range(len(board))
            if board[i][j] == 0
        ]
        for x, y in empty_cells:
            score += self.evaluate_move(board, x, y, player)
        return score

    def evaluate_board(self, player, board):
        return self.evaluate_board_each(player, board) - self.evaluate_board_each(3 - player, board)


    def make_move(self, board):
        candidate_moves = self.get_candidate_moves(board)
        if not candidate_moves:
            return None, None

        self_winning_move = self.find_winning_move(board, self.player, candidate_moves)
        if self_winning_move is not None:
            return self_winning_move, None

        oppo_winning_move = self.find_winning_move(board, self.opponent, candidate_moves)
        if oppo_winning_move is not None:
            return oppo_winning_move, None

        search_depth = self.choose_search_depth(board)

        _, best_move = self.alphabeta(
            board,
            depth=search_depth,
            alpha=float("-inf"),
            beta=float("inf"),
            maximizing_player=True,
            current_player=self.player,
        )

        if best_move is None:
            return candidate_moves[0], None
        return best_move, None


#python3 gomoku.py -m human
#python3 gomoku.py -m test_agent
