import argparse
import importlib
import numpy as np
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

PLAYER_TIME_LIMIT = 60.0
EMPTY = 0
PLAYER1_STONE = 1
PLAYER2_STONE = 2
PLAYER1_SKILL = 3
PLAYER2_SKILL = 4


def get_skill_marker(player):
    return PLAYER1_SKILL if player == 1 else PLAYER2_SKILL


def is_stone_cell(cell_value):
    return cell_value in (PLAYER1_STONE, PLAYER2_STONE)


def create_board(board_size=15):
    """
    创建棋盘

    @param board_size: 棋盘大小, 默认15x15(标准五子棋棋盘)
    @return: 棋盘数组
    """
    return np.zeros((board_size, board_size), dtype=int)


def is_valid_move(board, row, col):
    """
    检查移动是否有效

    @param board: 棋盘
    @param row: 行坐标
    @param col: 列坐标
    @return: 是否有效
    """
    return is_valid_position(board, row, col) and board[row][col] == EMPTY


def is_valid_position(board, row, col):
    """
    检查坐标是否在棋盘范围内

    @param board: 棋盘
    @param row: 行坐标
    @param col: 列坐标
    @return: 是否在范围内
    """
    board_size = len(board)
    return 0 <= row < board_size and 0 <= col < board_size


def make_move(board, row, col, player):
    """
    在指定位置落子

    @param board: 棋盘
    @param row: 行坐标
    @param col: 列坐标
    @param player: 玩家编号 (1或2)
    @return: 是否成功落子
    """
    if not is_valid_move(board, row, col):
        return False

    board[row][col] = player
    return True


def is_valid_skill_target(board, row, col):
    """
    检查技能释放位置是否合法（允许释放在技能标记位置，不允许释放在已有棋子位置）

    @param board: 棋盘
    @param row: 行坐标
    @param col: 列坐标
    @return: 是否合法
    """
    return is_valid_position(board, row, col) and not is_stone_cell(board[row][col])


def clear_block_for_player(board, blocked_cell_for_player, player):
    """
    清除对指定玩家的封锁效果（若棋盘上仍是对应封锁标记）

    @param board: 棋盘
    @param blocked_cell_for_player: 各玩家当前被封锁位置
    @param player: 被封锁玩家编号
    """
    blocked_cell = blocked_cell_for_player[player]
    if blocked_cell is None:
        return

    row, col = blocked_cell
    caster = 3 - player
    expected_marker = get_skill_marker(caster)
    if is_valid_position(board, row, col) and board[row][col] == expected_marker:
        board[row][col] = EMPTY

    blocked_cell_for_player[player] = None


def is_board_full(board):
    """
    检查棋盘是否已满

    @param board: 棋盘
    @return: 是否已满
    """
    return np.all((board == PLAYER1_STONE) | (board == PLAYER2_STONE))


def check_win(board, row, col):
    """
    检查从指定位置是否形成五子连珠

    @param board: 棋盘
    @param row: 最后落子的行坐标
    @param col: 最后落子的列坐标
    @return: 是否获胜
    """
    board_size = len(board)
    player = board[row][col]

    directions = [
        (0, 1),
        (1, 0),
        (1, 1),
        (1, -1),
    ]

    for dx, dy in directions:
        count = 1

        x, y = row + dx, col + dy
        while 0 <= x < board_size and 0 <= y < board_size and board[x][y] == player:
            count += 1
            x, y = x + dx, y + dy

        x, y = row - dx, col - dy
        while 0 <= x < board_size and 0 <= y < board_size and board[x][y] == player:
            count += 1
            x, y = x - dx, y - dy

        if count >= 5:
            return True

    return False


def print_board(board):
    """
    打印棋盘

    @param board: 棋盘
    """
    board_size = len(board)
    print("  ", end="")
    for j in range(board_size):
        print(f"{j:2}", end="")
    print()

    for i in range(board_size):
        print(f"{i:2}", end="")
        for j in range(board_size):
            if board[i][j] == 0:
                print(" .", end="")
            elif board[i][j] == 1:
                print(" ●", end="")
            elif board[i][j] == 2:
                print(" ○", end="")
            elif board[i][j] == 3:
                print(" ◆", end="")
            else:
                print(" ◇", end="")
        print()


def play_game(agent1=None, agent2=None, board_size=15):
    """
    进行一局游戏

    @param agent1: 玩家1的Agent, 如果为None则使用默认Agent
    @param agent2: 玩家2的Agent, 如果为None则使用默认Agent
    @param board_size: 棋盘大小, 默认15x15(标准五子棋棋盘)
    """
    board = create_board(board_size)
    current_player = 1
    game_over = False
    winner = None

    agents = {1: agent1, 2: agent2}
    skill_used = {1: False, 2: False}
    blocked_cell_for_player = {1: None, 2: None}

    print("游戏开始! ")
    print(f"玩家操作时间限制: {PLAYER_TIME_LIMIT}秒")
    print_board(board)

    while not game_over:
        print(f"\n轮到玩家 {current_player} (Agent {current_player})")

        current_agent = agents[current_player]

        start_time = time.time()

        is_human_player = hasattr(current_agent, "create_gui")

        if is_human_player:
            try:
                move_result = current_agent.make_move(board.copy())
                end_time = time.time()
                print(f"玩家 {current_player} 落子时间: {end_time - start_time:.4f}秒")
            except Exception as e:
                print(f"玩家 {current_player} 出现异常: {e}")
                winner = 3 - current_player
                game_over = True
                break
        else:
            with ThreadPoolExecutor(max_workers=1) as executor:
                try:
                    future = executor.submit(current_agent.make_move, board.copy())
                    move_result = future.result(timeout=PLAYER_TIME_LIMIT)
                    end_time = time.time()

                    print(
                        f"玩家 {current_player} 落子时间: {end_time - start_time:.4f}秒"
                    )

                except FutureTimeoutError:
                    end_time = time.time()
                    print(
                        f"玩家 {current_player} 操作超时! 超时时间: {end_time - start_time:.4f}秒"
                    )
                    print(
                        f"超过了 {PLAYER_TIME_LIMIT}秒的时间限制，玩家 {current_player} 败北!"
                    )
                    winner = 3 - current_player
                    game_over = True
                    break
                except Exception as e:
                    print(f"玩家 {current_player} 出现异常: {e}")
                    winner = 3 - current_player
                    game_over = True
                    break

        if game_over:
            break

        move = None
        skill_target = None

        if isinstance(move_result, tuple) and len(move_result) == 2:
            move, skill_target = move_result
        else:
            print("Agent返回值格式错误，应为((row,col), skill_pos|None)! ")
            winner = 3 - current_player
            break

        if skill_target is not None:
            if skill_used[current_player]:
                print(f"玩家 {current_player} 重复释放技能，技能无效但已消耗。")
            else:
                skill_used[current_player] = True
                if (
                    not isinstance(skill_target, (tuple, list))
                    or len(skill_target) != 2
                ):
                    print(f"玩家 {current_player} 技能释放格式非法，技能已消耗。")
                else:
                    skill_row, skill_col = skill_target
                    if not is_valid_skill_target(board, skill_row, skill_col):
                        print(
                            f"玩家 {current_player} 技能释放非法: ({skill_row}, {skill_col})，技能已消耗。"
                        )
                    else:
                        blocked_cell_for_player[3 - current_player] = (
                            skill_row,
                            skill_col,
                        )
                        board[skill_row][skill_col] = get_skill_marker(current_player)
                        print(
                            f"玩家 {current_player} 释放技能，封锁玩家 {3 - current_player} 下一回合位置 ({skill_row}, {skill_col})"
                        )


        if not (
            isinstance(move, (tuple, list))
            and len(move) == 2
            and isinstance(move[0], (int, np.integer))
            and isinstance(move[1], (int, np.integer))
        ):
            print("Agent落子格式错误，应为(row,col)! ")
            winner = 3 - current_player
            break

        row, col = move

        blocked_cell = blocked_cell_for_player[current_player]
        if blocked_cell is not None and (row, col) == blocked_cell:
            winner = 3 - current_player
            print(f"玩家 {current_player} 尝试在被封锁位置 ({row}, {col}) 落子，判负! ")
            break

        if not is_valid_move(board, row, col):
            winner = 3 - current_player
            print(f"无效的移动: ({row}, {col}), 对手(Agent {winner})获胜! ")
            break

        make_move(board, row, col, current_player)
        print(f"玩家 {current_player} 在 ({row}, {col}) 落子")
        print_board(board)

        if check_win(board, row, col):
            game_over = True
            winner = current_player
            print(f"玩家 {current_player} 获胜! ")
        elif is_board_full(board):
            game_over = True
            winner = 0
            print("游戏平局! ")
        else:
            clear_block_for_player(board, blocked_cell_for_player, current_player)
            current_player = 3 - current_player

    if winner == 0:
        print("\n游戏结果: 平局! ")
    elif winner:
        print(f"\n游戏结果: 玩家 {winner} 获胜! ")

    return winner


def main():
    """主函数, 演示游戏使用"""
    parser = argparse.ArgumentParser(description="五子棋对战")
    parser.add_argument(
        "-m",
        "--method",
        type=str,
        default="random",
        help="A2算法选择: human(人类) 或 xxx(算法模块名)",
    )
    parser.add_argument("-s", "--size", type=int, default=11, help="棋盘大小")
    args = parser.parse_args()

    board_size = args.size
    print(f"创建 {board_size}x{board_size} 的棋盘")

    from student import Search as A1  # TODO: fill in the name of your file

    # from human import Human as A1  # 人人对战

    agent1 = A1(1)

    if args.method == "human":
        from human import Human

        agent2 = Human(2)
    elif args.method == "random":
        from agent import Agent

        agent2 = Agent(2)
    else:
        try:
            mod = importlib.import_module(f"{args.method}")
            agent2 = mod.Search(2)
        except Exception as e:
            print(f"无法加载gomoku/{args.method}.py 的Search类: {e}")
            print("请确认该文件存在且有Search类")
            return

    play_game(agent1, agent2, board_size)


if __name__ == "__main__":
    main()
