from agent import Agent
import tkinter as tk
from tkinter import messagebox
import threading
import time


class Human(Agent):
    def __init__(self, player):
        super().__init__(player)
        self.selected_move = None
        self.waiting_for_move = False
        self.root = None
        self.canvas = None
        self.status_label = None
        self.board_size = 0
        self.cell_size = 30
        self.margin = 40
        self.canvas_size = 0
        self.surrendered = False
        self.skill_button = None
        self.skill_used = False
        self.skill_mode = False
        self.skill_target = None
        self.current_board = None

    def create_gui(self, board):
        """创建GUI棋盘界面"""
        self.current_board = board
        self.board_size = len(board)

        if self.board_size <= 9:
            self.cell_size = 40
        elif self.board_size <= 15:
            self.cell_size = 30
        else:
            self.cell_size = 25

        self.canvas_size = (self.board_size - 1) * self.cell_size + 2 * self.margin

        if self.root is None:
            self.root = tk.Tk()
            self.root.title(f"五子棋 - 人类玩家 ({self.board_size}x{self.board_size})")

            window_width = self.canvas_size + 40
            window_height = self.canvas_size + 90
            self.root.geometry(f"{window_width}x{window_height}")
            self.root.resizable(False, False)

            self.canvas = tk.Canvas(
                self.root,
                width=self.canvas_size,
                height=self.canvas_size,
                bg="burlywood",
                highlightthickness=2,
                highlightbackground="black",
            )
            self.canvas.pack(pady=20)

            self.skill_button = tk.Button(
                self.root,
                text="释放技能",
                width=12,
                command=self.activate_skill,
            )
            self.skill_button.pack(pady=5)

            self.canvas.bind("<Button-1>", self.on_canvas_click)

            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.draw_board(board)
        self.update_skill_button_state()

    def activate_skill(self):
        """进入技能释放模式（下次点击棋盘作为技能目标）。"""
        if self.skill_used or not self.waiting_for_move:
            return
        self.skill_mode = True
        self.update_skill_button_state()

    def update_skill_button_state(self):
        """更新技能按钮视觉状态。"""
        if self.skill_button is None:
            return

        if self.skill_used:
            self.skill_button.config(
                text="技能已释放", state=tk.DISABLED, relief=tk.SUNKEN
            )
        elif self.skill_mode:
            self.skill_button.config(
                text="请选择技能位置", state=tk.NORMAL, relief=tk.SUNKEN
            )
        else:
            self.skill_button.config(text="释放技能", state=tk.NORMAL, relief=tk.RAISED)

    def draw_board(self, board):
        """绘制棋盘"""
        if self.canvas is None:
            return

        self.canvas.delete("all")

        for i in range(self.board_size):
            x = self.margin + i * self.cell_size
            self.canvas.create_line(
                x,
                self.margin,
                x,
                self.margin + (self.board_size - 1) * self.cell_size,
                fill="black",
                width=1,
            )
            y = self.margin + i * self.cell_size
            self.canvas.create_line(
                self.margin,
                y,
                self.margin + (self.board_size - 1) * self.cell_size,
                y,
                fill="black",
                width=1,
            )

        for i in range(self.board_size):
            for j in range(self.board_size):
                if board[i][j] in (1, 2):
                    self.draw_stone(i, j, board[i][j])
                elif board[i][j] == 3:
                    self.draw_skill_stone(i, j, 1)
                elif board[i][j] == 4:
                    self.draw_skill_stone(i, j, 2)

        if self.skill_target is not None:
            skill_row, skill_col = self.skill_target
            if 0 <= skill_row < self.board_size and 0 <= skill_col < self.board_size:
                if board[skill_row][skill_col] == 0:
                    self.draw_skill_stone(skill_row, skill_col, self.player)

        font_size = min(max(8, self.cell_size // 3), 12)
        for i in range(self.board_size):
            y = self.margin + i * self.cell_size
            self.canvas.create_text(
                20, y, text=str(i), font=("Arial", font_size), fill="black"
            )
            x = self.margin + i * self.cell_size
            self.canvas.create_text(
                x, 20, text=str(i), font=("Arial", font_size), fill="black"
            )

    def draw_stone(self, row, col, player):
        """在指定位置绘制棋子"""
        x = self.margin + col * self.cell_size
        y = self.margin + row * self.cell_size
        radius = max(self.cell_size // 2 - 3, 8)

        if player == 1:
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="white",
                outline="black",
                width=2,
            )
        else:
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="black",
                outline="gray",
                width=2,
            )

    def draw_skill_stone(self, row, col, player):
        """在指定位置绘制技能标记（半透明效果）。"""
        x = self.margin + col * self.cell_size
        y = self.margin + row * self.cell_size
        radius = max(self.cell_size // 2 - 3, 8)

        if player == 1:
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="#f4ead1",
                outline="black",
                width=2,
                dash=(3, 2),
            )
        else:
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="#6b6b6b",
                outline="#2f2f2f",
                width=2,
                dash=(3, 2),
            )

    def on_canvas_click(self, event):
        """处理画布点击事件"""
        if not self.waiting_for_move:
            return

        col = round((event.x - self.margin) / self.cell_size)
        row = round((event.y - self.margin) / self.cell_size)

        if 0 <= row < self.board_size and 0 <= col < self.board_size:
            nearest_x = self.margin + col * self.cell_size
            nearest_y = self.margin + row * self.cell_size
            distance = ((event.x - nearest_x) ** 2 + (event.y - nearest_y) ** 2) ** 0.5

            if distance <= self.cell_size / 3:
                if self.skill_mode and not self.skill_used:
                    self.skill_target = (row, col)
                    self.skill_used = True
                    self.skill_mode = False
                    self.update_skill_button_state()
                    if self.current_board is not None:
                        self.draw_board(self.current_board)
                else:
                    self.selected_move = (row, col)
                    self.waiting_for_move = False

    def on_closing(self):
        """处理窗口关闭事件 - 关闭窗口视为认输"""
        if self.waiting_for_move:
            self.selected_move = None
            self.waiting_for_move = False
            self.surrendered = True
            print(f"玩家 {self.player} 关闭窗口，视为认输！")
        if self.root:
            self.root.destroy()
            self.root = None
            self.canvas = None
            self.status_label = None
            self.skill_button = None

    def make_move(self, board):
        """
        在棋盘上下一步棋。

        @param board: 表示游戏棋盘的二维列表
        @return 二元组: (落子位置, 技能位置)
                - 落子位置: (行, 列)
                - 技能位置: (行, 列) 或 None
        """
        if self.surrendered:
            return None, None

        self.create_gui(board)

        self.selected_move = None
        self.waiting_for_move = True
        self.skill_mode = False
        self.skill_target = None
        self.update_skill_button_state()

        while self.waiting_for_move and self.root:
            try:
                self.root.update()
                time.sleep(0.01)
            except tk.TclError:
                break

        if self.surrendered:
            return None, None

        if self.selected_move is None:
            empty_cells = [
                (i, j)
                for i in range(len(board))
                for j in range(len(board))
                if board[i][j] == 0
            ]
            if empty_cells:
                import random

                return random.choice(empty_cells), self.skill_target
            return None, self.skill_target

        return self.selected_move, self.skill_target


if __name__ == "__main__":
    import numpy as np

    human_player = Human(player=1)
    board1 = np.array(
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 2, 2, 2, 2, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
    )
    move = human_player.make_move(board1)
