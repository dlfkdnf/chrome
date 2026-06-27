import pygame
import sys
import random
import json
import os
from enum import Enum
from typing import List, Tuple, Optional
from collections import deque

# 초기화
pygame.init()

# 상수
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
GRID_WIDTH = 10
GRID_HEIGHT = 20
BLOCK_SIZE = 30
BOARD_LEFT = 50
BOARD_TOP = 50

# 색상
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
LIGHT_GRAY = (200, 200, 200)
RED = (240, 0, 0)
YELLOW = (240, 240, 0)

# 블록 색상들
COLORS = [
    (0, 240, 240),    # I - 시안
    (240, 240, 0),    # O - 노랑
    (160, 0, 240),    # T - 보라
    (0, 0, 240),      # J - 파랑
    (240, 160, 0),    # L - 주황
    (0, 240, 0),      # S - 녹색
    (240, 0, 0)       # Z - 빨강
]

# 테트로미노 정의
TETROMINOES = [
    # I
    [
        [(0, 0), (1, 0), (2, 0), (3, 0)],
        [(0, 0), (0, 1), (0, 2), (0, 3)]
    ],

    # O
    [
        [(0, 0), (1, 0), (0, 1), (1, 1)]
    ],

    # T
    [
        [(1, 0), (0, 1), (1, 1), (2, 1)],  # 위
        [(1, 0), (1, 1), (2, 1), (1, 2)],  # 우
        [(0, 1), (1, 1), (2, 1), (1, 2)],  # 아래
        [(1, 0), (0, 1), (1, 1), (1, 2)]   # 좌
    ],

    # J
    [
        [(0, 0), (0, 1), (1, 1), (2, 1)],  # 위
        [(1, 0), (2, 0), (1, 1), (1, 2)],  # 우
        [(0, 1), (1, 1), (2, 1), (2, 2)],  # 아래
        [(1, 0), (1, 1), (0, 2), (1, 2)]   # 좌
    ],

    # L
    [
        [(2, 0), (0, 1), (1, 1), (2, 1)],  # 위
        [(1, 0), (1, 1), (1, 2), (2, 2)],  # 우
        [(0, 1), (1, 1), (2, 1), (0, 2)],  # 아래
        [(0, 0), (1, 0), (1, 1), (1, 2)]   # 좌
    ],

    # S
    [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(0, 0), (0, 1), (1, 1), (1, 2)]
    ],

    # Z
    [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(1, 0), (0, 1), (1, 1), (0, 2)]
    ]
]

# SRS (Super Rotation System) Wall Kick Data
WALL_KICK_DATA = {
    'JLSTZ': {
        (0, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
        (1, 2): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
        (2, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
        (3, 0): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    },
    'I': {
        (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
        (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
        (2, 3): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
        (3, 0): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    }
}

class GameState(Enum):
    MENU = 1
    PLAYING = 2
    GAME_OVER = 3
    PAUSED = 4

class ScorePopup:
    """점수 팝업 애니메이션"""
    def __init__(self, x, y, score, text=""):
        self.x = x
        self.y = y
        self.score = score
        self.text = text
        self.lifetime = 60  # 프레임
        self.age = 0

    def update(self):
        self.age += 1
        return self.age < self.lifetime

    def get_alpha(self):
        return int(255 * (1 - self.age / self.lifetime))

    def get_y(self):
        return self.y - (self.age * 0.5)

class LineRemovalEffect:
    """라인 제거 이펙트"""
    def __init__(self):
        self.lines_to_remove = []
        self.animation_frame = 0
        self.animation_duration = 20

    def start(self, lines):
        self.lines_to_remove = lines
        self.animation_frame = 0

    def update(self):
        self.animation_frame += 1
        return self.animation_frame < self.animation_duration

    def is_animating(self):
        return self.animation_frame < self.animation_duration

    def get_progress(self):
        return self.animation_frame / self.animation_duration

class TetrisGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("TETRIS - Advanced")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        self.font_tiny = pygame.font.Font(None, 20)

        self.state = GameState.MENU
        self.high_score = self.load_high_score()
        self.reset_game()

        # 입력 제어용
        self.left_pressed_frames = 0
        self.right_pressed_frames = 0
        self.down_pressed_frames = 0

        # 이펙트
        self.score_popups = []
        self.line_removal_effect = LineRemovalEffect()

    def load_high_score(self):
        """최고점 불러오기"""
        try:
            if os.path.exists("high_score.json"):
                with open("high_score.json", "r") as f:
                    data = json.load(f)
                    return data.get("high_score", 0)
        except:
            pass
        return 0

    def save_high_score(self):
        """최고점 저장"""
        try:
            with open("high_score.json", "w") as f:
                json.dump({"high_score": self.high_score}, f)
        except:
            pass

    def reset_game(self):
        self.board = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        
        # 7-Bag 랜덤
        self.bag = list(range(len(TETROMINOES)))
        random.shuffle(self.bag)
        self.bag_index = 0
        
        self.current_piece = self.get_next_bag_piece()
        self.current_x = GRID_WIDTH // 2 - 2
        self.current_y = 0
        self.current_rotation = 0
        
        self.next_pieces = deque([self.get_next_bag_piece() for _ in range(3)])

        self.score = 0
        self.combo = 0
        self.last_clear_frame = -1000
        self.level = 1
        self.lines_cleared_total = 0
        self.back_to_back = False
        self.last_clear_was_tetris = False

        # 속도 관련
        self.fall_speed = 0.5
        self.frames_passed = 0

        # Lock 타이머 (간단한 시스템)
        self.lock_timer = None  # 땅에 닿은 시간 저장
        self.LOCK_DELAY = 1.0  # 1초

        self.game_over = False
        self.game_over_time = 0
        self.paused = False
        self.pause_time = 0

        # 입력 제어용 초기화
        self.left_pressed_frames = 0
        self.right_pressed_frames = 0
        self.down_pressed_frames = 0

        # T-Spin 판정용
        self.last_rotation_was_kick = False
        self.last_move_was_rotation = False

    def get_next_bag_piece(self):
        """7-Bag 랜덤 방식으로 다음 피스 획득"""
        if self.bag_index >= len(self.bag):
            self.bag = list(range(len(TETROMINOES)))
            random.shuffle(self.bag)
            self.bag_index = 0
        
        piece_type = self.bag[self.bag_index]
        self.bag_index += 1
        return (piece_type, 0)

    def get_piece_blocks(self, piece_type, rotation):
        """현재 피스의 블록 좌표 반환"""
        if piece_type < len(TETROMINOES):
            shapes = TETROMINOES[piece_type]
            if rotation < len(shapes):
                return shapes[rotation]
        return TETROMINOES[piece_type][0]

    def get_current_blocks(self):
        """현재 피스의 월드 좌표 반환"""
        piece_type, rotation = self.current_piece
        blocks = self.get_piece_blocks(piece_type, rotation)
        return [(self.current_x + x, self.current_y + y) for x, y in blocks]

    def is_valid_position(self, x, y, piece_type, rotation):
        """주어진 위치에 피스를 놓을 수 있는지 확인"""
        blocks = self.get_piece_blocks(piece_type, rotation)
        for bx, by in blocks:
            world_x = x + bx
            world_y = y + by

            if world_x < 0 or world_x >= GRID_WIDTH:
                return False
            if world_y >= GRID_HEIGHT:
                return False
            if world_y >= 0 and self.board[world_y][world_x] != 0:
                return False

        return True

    def get_wall_kick_tests(self, piece_type, from_rotation, to_rotation):
        """Wall Kick 테스트 데이터 반환"""
        if piece_type == 0:  # I
            key = 'I'
        else:
            key = 'JLSTZ'
        
        kick_data = WALL_KICK_DATA.get(key, {})
        return kick_data.get((from_rotation, to_rotation), [(0, 0)])

    def try_rotation_with_wall_kick(self, new_rotation):
        """Wall Kick을 포함한 회전 시도"""
        piece_type = self.current_piece[0]
        old_rotation = self.current_piece[1]

        # 먼저 일반 회전 시도
        if self.is_valid_position(self.current_x, self.current_y, piece_type, new_rotation):
            self.current_piece = (piece_type, new_rotation)
            self.last_rotation_was_kick = False
            self.last_move_was_rotation = True
            return True

        # Wall Kick 시도
        kick_tests = self.get_wall_kick_tests(piece_type, old_rotation, new_rotation)
        for kick_x, kick_y in kick_tests:
            if self.is_valid_position(self.current_x + kick_x, self.current_y + kick_y,
                                     piece_type, new_rotation):
                self.current_x += kick_x
                self.current_y += kick_y
                self.current_piece = (piece_type, new_rotation)
                self.last_rotation_was_kick = True
                self.last_move_was_rotation = True
                return True

        return False

    def hard_drop(self):
        """Hard Drop - 즉시 바닥에 떨어짐"""
        drop_distance = 0
        while self.is_valid_position(self.current_x, self.current_y + drop_distance + 1,
                                     self.current_piece[0], self.current_piece[1]):
            drop_distance += 1
        
        self.current_y += drop_distance
        # Hard Drop 점수: 떨어진 거리 * 2
        self.score += drop_distance * 2
        self.score_popups.append(ScorePopup(WINDOW_WIDTH // 2, 80, drop_distance * 2, f"+{drop_distance * 2}"))
        self.lock_piece()

    def lock_piece(self):
        """현재 피스를 보드에 고정"""
        piece_type, rotation = self.current_piece
        blocks = self.get_current_blocks()

        for x, y in blocks:
            if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
                self.board[y][x] = piece_type + 1

        # 블록 설치 시 점수 (한번만)
        self.score += 30
        self.score_popups.append(ScorePopup(WINDOW_WIDTH // 2, 80, 30, "+30"))
        
        # 다음 피스 설정
        self.current_piece = self.next_pieces.popleft()
        self.next_pieces.append(self.get_next_bag_piece())
        self.current_x = GRID_WIDTH // 2 - 2
        self.current_y = 0
        self.current_rotation = 0

        # Lock 타이머 초기화
        self.lock_timer = None
        self.last_move_was_rotation = False

    def detect_t_spin(self):
        """T-Spin 판정"""
        piece_type, rotation = self.current_piece
        if piece_type != 2:  # T 피스가 아니면 T-Spin 불가
            return False

        if not self.last_rotation_was_kick:
            return False

        return True

    def clear_lines(self):
        """채워진 줄 제거 및 점수 계산"""
        lines_to_clear = []
        
        for y in range(GRID_HEIGHT):
            if all(cell != 0 for cell in self.board[y]):
                lines_to_clear.append(y)

        lines_cleared = len(lines_to_clear)

        if lines_cleared > 0:
            # 라인 제거 이펙트 시작
            self.line_removal_effect.start(lines_to_clear)

            # 라인 제거
            new_board = []
            for y in range(GRID_HEIGHT):
                if y not in lines_to_clear:
                    new_board.append(self.board[y][:])
            
            # 위에 빈 줄 추가
            for _ in range(lines_cleared):
                new_board.insert(0, [0 for _ in range(GRID_WIDTH)])
            
            self.board = new_board

            # 점수 계산
            base_scores = [0, 100, 300, 500, 1000]
            base_score = base_scores[min(lines_cleared, 4)]

            # Tetris (4줄) 보너스
            is_tetris = (lines_cleared == 4)
            if is_tetris:
                base_score = 1000

            # Back-to-Back 보너스
            if (is_tetris or lines_cleared == 3) and self.back_to_back:
                base_score = int(base_score * 1.5)

            # 콤보 보너스
            frames_since_last_clear = self.frames_passed - self.last_clear_frame
            if frames_since_last_clear <= 120:
                self.combo += 1
            else:
                self.combo = 1

            combo_bonuses = [0, 50, 100, 200, 400]
            combo_bonus = combo_bonuses[min(self.combo - 1, 4)]

            # T-Spin 감지
            t_spin = self.detect_t_spin()
            if t_spin:
                base_score = int(base_score * 1.6)  # T-Spin 보너스
                self.score_popups.append(ScorePopup(WINDOW_WIDTH // 2, 100, 0, "T-SPIN!"))

            # 최종 점수
            line_score = base_score
            combo_score = int(line_score * combo_bonus / 100)
            total_score = line_score + combo_score

            self.score += total_score
            self.lines_cleared_total += lines_cleared
            self.update_level()

            # 팝업 추가
            if is_tetris:
                self.score_popups.append(ScorePopup(WINDOW_WIDTH // 2, 80, total_score, "TETRIS!"))
            else:
                self.score_popups.append(ScorePopup(WINDOW_WIDTH // 2, 80, total_score, f"+{total_score}"))

            print(f"Lines: {lines_cleared}, Score: {total_score}, Total: {self.score}, Combo: {self.combo}")

            self.last_clear_frame = self.frames_passed
            self.last_clear_was_tetris = is_tetris
            self.back_to_back = is_tetris or lines_cleared == 3
        else:
            self.combo = 0
            self.back_to_back = False

        return lines_cleared

    def check_all_clear(self):
        """all clear 확인"""
        if all(cell == 0 for row in self.board for cell in row):
            self.score += 1500
            self.combo = 0
            self.score_popups.append(ScorePopup(WINDOW_WIDTH // 2, 100, 1500, "ALL CLEAR!"))
            print(f"ALL CLEAR! +1500 points. Total: {self.score}")
            return True
        return False

    def update_level(self):
        """레벨 업데이트"""
        self.level = 1 + (self.lines_cleared_total // 10)

    def update_speed(self):
        """속도 업데이트 (레벨에 따라)"""
        # 레벨당 0.1씩 증가
        base_speed = 0.5
        speed_increase = (self.level - 1) * 0.1
        self.fall_speed = min(base_speed + speed_increase, 20.0)

    def handle_input(self):
        """입력 처리"""
        keys = pygame.key.get_pressed()

        if self.state == GameState.PLAYING:
            # 좌우 이동
            if keys[pygame.K_LEFT]:
                self.left_pressed_frames += 1
                if self.left_pressed_frames == 1 or self.left_pressed_frames > 20:
                    if self.is_valid_position(self.current_x - 1, self.current_y,
                                             self.current_piece[0], self.current_piece[1]):
                        self.current_x -= 1
            else:
                self.left_pressed_frames = 0

            if keys[pygame.K_RIGHT]:
                self.right_pressed_frames += 1
                if self.right_pressed_frames == 1 or self.right_pressed_frames > 20:
                    if self.is_valid_position(self.current_x + 1, self.current_y,
                                             self.current_piece[0], self.current_piece[1]):
                        self.current_x += 1
            else:
                self.right_pressed_frames = 0

            # Soft Drop (아래로 누르기) - 5프레임마다 한 칸씩
            if keys[pygame.K_DOWN]:
                self.down_pressed_frames += 1
                if self.down_pressed_frames % 5 == 1:
                    if self.is_valid_position(self.current_x, self.current_y + 1,
                                             self.current_piece[0], self.current_piece[1]):
                        self.current_y += 1
            else:
                self.down_pressed_frames = 0

        # 이벤트 처리
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU:
                    if event.key == pygame.K_SPACE:
                        self.state = GameState.PLAYING
                        self.reset_game()

                elif self.state == GameState.PLAYING:
                    # 회전 (위쪽 방향키)
                    if event.key == pygame.K_UP:
                        new_rotation = (self.current_piece[1] + 1) % len(TETROMINOES[self.current_piece[0]])
                        self.try_rotation_with_wall_kick(new_rotation)

                    # Hard Drop (스페이스)
                    elif event.key == pygame.K_SPACE:
                        self.hard_drop()

                    # Pause (P)
                    elif event.key == pygame.K_p:
                        self.state = GameState.PAUSED
                        self.pause_time = pygame.time.get_ticks()

                    # ESC 메뉴로 복귀
                    elif event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU

                elif self.state == GameState.PAUSED:
                    # P로 재개
                    if event.key == pygame.K_p:
                        self.state = GameState.PLAYING

                    # ESC 메뉴로 복귀
                    elif event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU

                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_RETURN:
                        self.state = GameState.PLAYING
                        self.reset_game()
                    elif event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU

        return True

    def update(self):
        """게임 로직 업데이트"""
        if self.state != GameState.PLAYING:
            return True

        self.frames_passed += 1

        # 블록 내려오기
        fall_interval = max(1, int(60 / self.fall_speed))
        if self.frames_passed % fall_interval == 0:
            if self.is_valid_position(self.current_x, self.current_y + 1,
                                     self.current_piece[0], self.current_piece[1]):
                self.current_y += 1
                self.lock_timer = None  # 떨어지면 타이머 초기화
            else:
                # 지면에 닿았을 때 - 타이머 시작
                if self.lock_timer is None:
                    self.lock_timer = pygame.time.get_ticks()

        # Lock 타이머 체크 - 1초 지났으면 설치
        if self.lock_timer is not None:
            elapsed_time = (pygame.time.get_ticks() - self.lock_timer) / 1000.0
            if elapsed_time >= self.LOCK_DELAY:
                self.lock_piece()
                self.clear_lines()
                self.check_all_clear()
                self.update_speed()

        # 게임오버 확인 (스폰 위치에서 배치 불가)
        if not self.is_valid_position(self.current_x, self.current_y,
                                     self.current_piece[0], self.current_piece[1]):
            self.state = GameState.GAME_OVER
            self.game_over_time = pygame.time.get_ticks()
            
            # 최고점 갱신
            if self.score > self.high_score:
                self.high_score = self.score
                self.save_high_score()

        # 점수 팝업 업데이트
        self.score_popups = [p for p in self.score_popups if p.update()]

        # 라인 제거 이펙트 업데이트
        if self.line_removal_effect.is_animating():
            self.line_removal_effect.update()

        return True

    def draw_board(self):
        """보드 그리기"""
        # 보드 배경
        pygame.draw.rect(self.screen, DARK_GRAY,
                        (BOARD_LEFT, BOARD_TOP,
                         GRID_WIDTH * BLOCK_SIZE, GRID_HEIGHT * BLOCK_SIZE))

        # 그리드
        for i in range(GRID_HEIGHT + 1):
            pygame.draw.line(self.screen, GRAY,
                           (BOARD_LEFT, BOARD_TOP + i * BLOCK_SIZE),
                           (BOARD_LEFT + GRID_WIDTH * BLOCK_SIZE, BOARD_TOP + i * BLOCK_SIZE))

        for i in range(GRID_WIDTH + 1):
            pygame.draw.line(self.screen, GRAY,
                           (BOARD_LEFT + i * BLOCK_SIZE, BOARD_TOP),
                           (BOARD_LEFT + i * BLOCK_SIZE, BOARD_TOP + GRID_HEIGHT * BLOCK_SIZE))

        # 보드 블록들
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.board[y][x] != 0:
                    # 라인 제거 애니메이션 중인지 확인
                    is_removing = y in self.line_removal_effect.lines_to_remove and \
                                 self.line_removal_effect.is_animating()

                    if is_removing:
                        # 깜박이는 효과
                        progress = self.line_removal_effect.get_progress()
                        if progress < 0.5:
                            continue
                    
                    color = COLORS[self.board[y][x] - 1]
                    pygame.draw.rect(self.screen, color,
                                   (BOARD_LEFT + x * BLOCK_SIZE, BOARD_TOP + y * BLOCK_SIZE,
                                    BLOCK_SIZE, BLOCK_SIZE))
                    pygame.draw.rect(self.screen, WHITE,
                                   (BOARD_LEFT + x * BLOCK_SIZE, BOARD_TOP + y * BLOCK_SIZE,
                                    BLOCK_SIZE, BLOCK_SIZE), 1)

        # 현재 피스
        piece_type, rotation = self.current_piece
        color = COLORS[piece_type]
        blocks = self.get_current_blocks()

        for x, y in blocks:
            if 0 <= y < GRID_HEIGHT:
                pygame.draw.rect(self.screen, color,
                               (BOARD_LEFT + x * BLOCK_SIZE, BOARD_TOP + y * BLOCK_SIZE,
                                BLOCK_SIZE, BLOCK_SIZE))
                pygame.draw.rect(self.screen, WHITE,
                               (BOARD_LEFT + x * BLOCK_SIZE, BOARD_TOP + y * BLOCK_SIZE,
                                BLOCK_SIZE, BLOCK_SIZE), 2)

        # 보드 테두리
        pygame.draw.rect(self.screen, WHITE,
                        (BOARD_LEFT, BOARD_TOP,
                         GRID_WIDTH * BLOCK_SIZE, GRID_HEIGHT * BLOCK_SIZE), 3)

    def draw_next_pieces(self):
        """다음 블록들 표시 (3개)"""
        next_x = BOARD_LEFT + GRID_WIDTH * BLOCK_SIZE + 50
        next_y = BOARD_TOP + 20

        # 제목
        next_text = self.font_small.render("NEXT", True, WHITE)
        self.screen.blit(next_text, (next_x, next_y))

        # 3개의 다음 블록 표시
        for i, piece_info in enumerate(self.next_pieces):
            piece_type, _ = piece_info
            color = COLORS[piece_type]
            blocks = self.get_piece_blocks(piece_type, 0)

            # 각 블록의 위치
            preview_y = next_y + 60 + i * 80

            # 배경
            pygame.draw.rect(self.screen, DARK_GRAY, (next_x, preview_y, 120, 70))
            pygame.draw.rect(self.screen, GRAY, (next_x, preview_y, 120, 70), 2)

            # 블록 그리기 (중앙 정렬)
            min_x = min(bx for bx, _ in blocks)
            min_y = min(by for _, by in blocks)
            
            for bx, by in blocks:
                px = next_x + 20 + (bx - min_x) * 20
                py = preview_y + 10 + (by - min_y) * 20
                pygame.draw.rect(self.screen, color, (px, py, 20, 20))
                pygame.draw.rect(self.screen, WHITE, (px, py, 20, 20), 1)

    def draw_info_panel(self):
        """정보 패널 그리기"""
        info_x = BOARD_LEFT + GRID_WIDTH * BLOCK_SIZE + 50
        info_y = BOARD_TOP + 380

        # 점수
        score_text = self.font_small.render("SCORE", True, WHITE)
        self.screen.blit(score_text, (info_x, info_y))

        score_value = self.font_medium.render(str(self.score), True, LIGHT_GRAY)
        self.screen.blit(score_value, (info_x, info_y + 30))

        # 최고점
        high_score_text = self.font_tiny.render(f"HIGH: {self.high_score}", True, GRAY)
        self.screen.blit(high_score_text, (info_x, info_y + 70))

        # 레벨
        level_y = info_y + 110
        level_text = self.font_small.render("LEVEL", True, WHITE)
        self.screen.blit(level_text, (info_x, level_y))

        level_value = self.font_medium.render(str(self.level), True, LIGHT_GRAY)
        self.screen.blit(level_value, (info_x, level_y + 30))

        # 라인
        lines_y = level_y + 80
        lines_text = self.font_small.render("LINES", True, WHITE)
        self.screen.blit(lines_text, (info_x, lines_y))

        lines_value = self.font_medium.render(str(self.lines_cleared_total), True, LIGHT_GRAY)
        self.screen.blit(lines_value, (info_x, lines_y + 30))

        # 콤보
        combo_y = lines_y + 80
        combo_text = self.font_small.render("COMBO", True, WHITE)
        self.screen.blit(combo_text, (info_x, combo_y))

        combo_color = YELLOW if self.combo > 0 else GRAY
        combo_value = self.font_medium.render(str(self.combo), True, combo_color)
        self.screen.blit(combo_value, (info_x, combo_y + 30))

        # Back-to-Back 표시
        if self.back_to_back:
            b2b_text = self.font_small.render("B2B", True, YELLOW)
            self.screen.blit(b2b_text, (info_x, combo_y + 70))

    def draw_menu(self):
        """메뉴 화면"""
        self.screen.fill(BLACK)

        title = self.font_large.render("TETRIS", True, WHITE)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)

        # 최고점 표시
        high_score_text = self.font_medium.render(f"HIGH SCORE: {self.high_score}", True, LIGHT_GRAY)
        high_score_rect = high_score_text.get_rect(center=(WINDOW_WIDTH // 2, 200))
        self.screen.blit(high_score_text, high_score_rect)

        start_text = self.font_medium.render("PRESS SPACE TO START", True, LIGHT_GRAY)
        start_rect = start_text.get_rect(center=(WINDOW_WIDTH // 2, 350))
        self.screen.blit(start_text, start_rect)

        # 조작법
        controls_y = 450
        controls = [
            "← → : Move | ↑ : Rotate | SPACE : Hard Drop",
            "↓ : Soft Drop | P : Pause | ESC : Menu"
        ]
        for i, control in enumerate(controls):
            control_text = self.font_tiny.render(control, True, GRAY)
            self.screen.blit(control_text, (WINDOW_WIDTH // 2 - control_text.get_width() // 2,
                                           controls_y + i * 25))

    def draw_pause(self):
        """일시정지 화면"""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))

        pause_text = self.font_large.render("PAUSED", True, WHITE)
        pause_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, 300))
        self.screen.blit(pause_text, pause_rect)

        resume_text = self.font_medium.render("PRESS P TO RESUME", True, LIGHT_GRAY)
        resume_rect = resume_text.get_rect(center=(WINDOW_WIDTH // 2, 400))
        self.screen.blit(resume_text, resume_rect)

        menu_text = self.font_small.render("ESC FOR MENU", True, GRAY)
        menu_rect = menu_text.get_rect(center=(WINDOW_WIDTH // 2, 450))
        self.screen.blit(menu_text, menu_rect)

    def draw_game_over(self):
        """게임오버 화면"""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))

        game_over_text = self.font_large.render("GAME OVER", True, RED)
        game_over_rect = game_over_text.get_rect(center=(WINDOW_WIDTH // 2, 150))
        self.screen.blit(game_over_text, game_over_rect)

        final_score_label = self.font_medium.render("FINAL SCORE", True, WHITE)
        final_score_rect = final_score_label.get_rect(center=(WINDOW_WIDTH // 2, 250))
        self.screen.blit(final_score_label, final_score_rect)

        final_score = self.font_large.render(str(self.score), True, LIGHT_GRAY)
        final_score_rect = final_score.get_rect(center=(WINDOW_WIDTH // 2, 320))
        self.screen.blit(final_score, final_score_rect)

        # 최고점 달성 메시지
        if self.score == self.high_score and self.score > 0:
            new_high_text = self.font_medium.render("NEW HIGH SCORE!", True, YELLOW)
            new_high_rect = new_high_text.get_rect(center=(WINDOW_WIDTH // 2, 380))
            self.screen.blit(new_high_text, new_high_rect)

        # 카운트다운
        elapsed_ms = pygame.time.get_ticks() - self.game_over_time
        remaining_seconds = max(0, 10 - elapsed_ms // 1000)

        if remaining_seconds > 0:
            countdown = self.font_medium.render(f"CONTINUE IN {remaining_seconds}s", True, LIGHT_GRAY)
            countdown_rect = countdown.get_rect(center=(WINDOW_WIDTH // 2, 450))
            self.screen.blit(countdown, countdown_rect)

            continue_text = self.font_small.render("(PRESS ENTER)", True, WHITE)
            continue_rect = continue_text.get_rect(center=(WINDOW_WIDTH // 2, 500))
            self.screen.blit(continue_text, continue_rect)

            if remaining_seconds == 0:
                self.state = GameState.MENU
        else:
            self.state = GameState.MENU

    def draw_score_popups(self):
        """점수 팝업 애니메이션 그리기"""
        for popup in self.score_popups:
            alpha = popup.get_alpha()
            y = int(popup.get_y())

            # 점수
            if popup.score > 0:
                score_text = self.font_medium.render(f"+{popup.score}", True, YELLOW)
            else:
                score_text = self.font_medium.render(popup.text, True, YELLOW)

            # 반투명 처리
            score_text.set_alpha(alpha)
            self.screen.blit(score_text, (popup.x - score_text.get_width() // 2, y))

    def draw(self):
        """화면 그리기"""
        self.screen.fill(BLACK)

        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state == GameState.PLAYING:
            self.draw_board()
            self.draw_next_pieces()
            self.draw_info_panel()
            self.draw_score_popups()
        elif self.state == GameState.PAUSED:
            self.draw_board()
            self.draw_next_pieces()
            self.draw_info_panel()
            self.draw_pause()
        elif self.state == GameState.GAME_OVER:
            self.draw_board()
            self.draw_next_pieces()
            self.draw_info_panel()
            self.draw_game_over()

        pygame.display.flip()

    def run(self):
        """메인 게임 루프"""
        running = True
        while running:
            running = self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = TetrisGame()
    game.run()