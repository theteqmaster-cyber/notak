import sys
import random
from PySide6.QtCore import Qt, QTimer, QRectF, Signal, QPointF
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, 
                             QGraphicsScene, QGraphicsItem, QGraphicsRectItem, 
                             QGraphicsTextItem, QStackedWidget, QGridLayout)
from PySide6.QtGui import QColor, QFont, QBrush, QPen, QPainter
from qfluentwidgets import (TitleLabel, SubtitleLabel, BodyLabel, TransparentPushButton, 
                            FluentIcon as FIF, ElevatedCardWidget, CardWidget, CaptionLabel, StrongBodyLabel)
from core.database import update_high_score, get_high_score

# --- GAME: SNAKE ---
class SnakeGame(QGraphicsView):
    gameOver = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(0, 0, 400, 400)
        self.setScene(self.scene)
        self.setFixedSize(405, 405)
        self.setStyleSheet("background: #111; border: 2px solid #333; border-radius: 12px;")
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.move_snake)
        
        self.reset_game()

    def reset_game(self):
        self.scene.clear()
        self.snake = [QPointF(5, 5), QPointF(5, 6), QPointF(5, 7)]
        self.direction = Qt.Key_Up
        self.food = self.spawn_food()
        self.score = 0
        self.is_running = False
        self.snake_items = []
        for p in self.snake:
            item = self.scene.addRect(p.x()*20, p.y()*20, 18, 18, QPen(Qt.NoPen), QBrush(QColor("#0078d4")))
            self.snake_items.append(item)
        
        self.food_item = self.scene.addRect(self.food.x()*20, self.food.y()*20, 18, 18, QPen(Qt.NoPen), QBrush(QColor("#ff4b2b")))
        
        self.msg = self.scene.addText("Press SPACE to Start", QFont("Segoe UI", 16))
        self.msg.setDefaultTextColor(Qt.white)
        self.msg.setPos(100, 180)

    def spawn_food(self):
        while True:
            p = QPointF(random.randint(0, 19), random.randint(0, 19))
            if p not in self.snake: return p

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Space and not self.is_running:
            self.start_game()
        elif key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            # Prevent 180 turns
            if (key == Qt.Key_Up and self.direction != Qt.Key_Down) or \
               (key == Qt.Key_Down and self.direction != Qt.Key_Up) or \
               (key == Qt.Key_Left and self.direction != Qt.Key_Right) or \
               (key == Qt.Key_Right and self.direction != Qt.Key_Left):
                self.direction = key

    def start_game(self):
        self.is_running = True
        self.msg.setVisible(False)
        self.timer.start(100)

    def move_snake(self):
        head = QPointF(self.snake[0])
        if self.direction == Qt.Key_Up: head.setY(head.y() - 1)
        elif self.direction == Qt.Key_Down: head.setY(head.y() + 1)
        elif self.direction == Qt.Key_Left: head.setX(head.x() - 1)
        elif self.direction == Qt.Key_Right: head.setX(head.x() + 1)
        
        # Collisions
        if head.x() < 0 or head.x() > 19 or head.y() < 0 or head.y() > 19 or head in self.snake:
            self.timer.stop()
            self.gameOver.emit(self.score)
            self.reset_game()
            return
            
        self.snake.insert(0, head)
        item = self.scene.addRect(head.x()*20, head.y()*20, 18, 18, QPen(Qt.NoPen), QBrush(QColor("#0078d4")))
        self.snake_items.insert(0, item)
        
        if head == self.food:
            self.score += 10
            self.food = self.spawn_food()
            self.food_item.setRect(self.food.x()*20, self.food.y()*20, 18, 18)
        else:
            self.snake.pop()
            old_item = self.snake_items.pop()
            self.scene.removeItem(old_item)

# --- GAME: ORBIT DODGE ---
class OrbitDodgeGame(QGraphicsView):
    gameOver = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(0, 0, 400, 400)
        self.setScene(self.scene)
        self.setFixedSize(405, 405)
        self.setStyleSheet("background: #050505; border-radius: 12px;")
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_game)
        self.reset_game()

    def reset_game(self):
        self.scene.clear()
        self.player = self.scene.addRect(180, 360, 40, 10, QPen(Qt.NoPen), QBrush(QColor("#0078d4")))
        self.enemies = []
        self.score = 0
        self.spawn_timer = 0
        self.is_running = False
        self.msg = self.scene.addText("Press SPACE to Start DODGE", QFont("Segoe UI", 14))
        self.msg.setDefaultTextColor(Qt.white)
        self.msg.setPos(80, 180)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not self.is_running:
            self.is_running = True
            self.msg.setVisible(False)
            self.timer.start(20)
        elif event.key() == Qt.Key_Left:
            if self.player.x() > -180: self.player.setX(self.player.x() - 20)
        elif event.key() == Qt.Key_Right:
            if self.player.x() < 180: self.player.setX(self.player.x() + 20)

    def update_game(self):
        self.score += 1
        self.spawn_timer += 1
        if self.spawn_timer > 30:
            self.spawn_timer = 0
            e = self.scene.addRect(random.randint(0, 380), -20, 20, 20, QPen(Qt.NoPen), QBrush(QColor("#ff4b2b")))
            self.enemies.append(e)
            
        for e in self.enemies[:]:
            e.moveBy(0, 5)
            if e.collidesWithItem(self.player):
                self.timer.stop()
                self.gameOver.emit(self.score // 10)
                self.reset_game()
                return
            if e.y() > 400:
                self.scene.removeItem(e)
                self.enemies.remove(e)

# --- GAME: MEMORY PULSE ---
class MemoryPulseGame(QWidget):
    gameOver = Signal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 400)
        self.layout = QGridLayout(self)
        self.layout.setSpacing(10)
        self.reset_game()

    def reset_game(self):
        # Clear layout
        while self.layout.count():
            self.layout.takeAt(0).widget().deleteLater()
        
        icons = [FIF.HEART, FIF.MUSIC, FIF.EDIT, FIF.FOLDER, FIF.PHOTO, FIF.DOCUMENT] * 2
        random.shuffle(icons)
        self.buttons = []
        self.selected = []
        self.matches = 0
        self.clicks = 0
        
        for i, icon in enumerate(icons):
            btn = TransparentPushButton(FIF.QUESTION, "")
            btn.setFixedSize(80, 80)
            btn.setStyleSheet("background: rgba(255,255,255,0.1); border-radius: 8px;")
            btn.setProperty("icon_data", icon)
            btn.clicked.connect(lambda checked=False, b=btn: self.on_click(b))
            self.layout.addWidget(btn, i // 4, i % 4)
            self.buttons.append(btn)

    def on_click(self, btn):
        if btn in self.selected or len(self.selected) >= 2 or btn.icon() != FIF.QUESTION:
            return
        
        btn.setIcon(btn.property("icon_data"))
        self.selected.append(btn)
        self.clicks += 1
        
        if len(self.selected) == 2:
            QTimer.singleShot(500, self.check_match)

    def check_match(self):
        b1, b2 = self.selected
        if b1.property("icon_data") == b2.property("icon_data"):
            self.matches += 1
            if self.matches == 6:
                score = max(0, 1000 - self.clicks * 10)
                self.gameOver.emit(score)
                self.reset_game()
        else:
            b1.setIcon(FIF.QUESTION)
            b2.setIcon(FIF.QUESTION)
        self.selected = []

# --- INTERFACE: GAMES HUB ---
class GamesInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("GamesInterface")
        self.setStyleSheet("background: transparent;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(60, 40, 60, 60)
        self.layout.setSpacing(30)
        
        # Header
        header = QHBoxLayout()
        v_h = QVBoxLayout()
        title_lbl = TitleLabel("MINI GAMES HAVEN")
        title_lbl.setStyleSheet("font-weight: 900; letter-spacing: -1px;")
        v_h.addWidget(title_lbl)
        v_h.addWidget(BodyLabel("Take a break. Challenge yourself. Beat your records."))
        header.addLayout(v_h)
        header.addStretch(1)
        self.layout.addLayout(header)
        
        # Main Area
        main_content = QHBoxLayout()
        
        # Game Selection
        self.selection_v = QVBoxLayout()
        self.selection_v.setSpacing(15)
        
        self.btn_snake = self.create_nav_btn("SNAKE MANIA", "snake_game")
        self.btn_dodge = self.create_nav_btn("ORBIT DODGE", "dodge_game")
        self.btn_memory = self.create_nav_btn("MEMORY PULSE", "memory_game")
        
        self.selection_v.addWidget(self.btn_snake)
        self.selection_v.addWidget(self.btn_dodge)
        self.selection_v.addWidget(self.btn_memory)
        self.selection_v.addStretch(1)
        
        main_content.addLayout(self.selection_v)
        
        # Game Display (using QStackedWidget to switch)
        self.display_card = CardWidget()
        self.display_card.setFixedSize(500, 500)
        self.display_card.setStyleSheet("""
            CardWidget {
                background: rgba(0, 0, 0, 0.7); 
                border-radius: 20px;
                border: 2px solid rgba(255, 255, 255, 0.1);
            }
        """)
        self.stack = QStackedWidget(self.display_card)
        self.stack.setFixedSize(420, 420)
        
        # Add games to stack
        self.snake_game = SnakeGame()
        self.dodge_game = OrbitDodgeGame()
        self.memory_game = MemoryPulseGame()
        
        self.stack.addWidget(self.snake_game)
        self.stack.addWidget(self.dodge_game)
        self.stack.addWidget(self.memory_game)
        
        # Connect game over signals
        self.snake_game.gameOver.connect(lambda s: self.handle_game_over("snake_game", s))
        self.dodge_game.gameOver.connect(lambda s: self.handle_game_over("dodge_game", s))
        self.memory_game.gameOver.connect(lambda s: self.handle_game_over("memory_game", s))
        
        # Center the stack in the card
        display_v = QVBoxLayout(self.display_card)
        display_v.setContentsMargins(40, 40, 40, 40)
        display_v.addWidget(self.stack, alignment=Qt.AlignCenter)
        
        main_content.addStretch(1)
        main_content.addWidget(self.display_card)
        main_content.addStretch(1)
        
        self.layout.addLayout(main_content)
        self.update_scores()

    def create_nav_btn(self, name, game_id):
        btn = ElevatedCardWidget()
        btn.setProperty("game_id", game_id)
        btn.setFixedSize(220, 90)
        btn.setCursor(Qt.PointingHandCursor)
        lyt = QVBoxLayout(btn)
        
        title = BodyLabel(name)
        title.setStyleSheet("font-weight: bold; font-size: 15px;")
        
        score_val = get_high_score(game_id)
        score_lbl = CaptionLabel(f"High Score: {score_val}")
        score_lbl.setObjectName(f"score_{game_id}")
        score_lbl.setStyleSheet("color: #0078d4;")
        
        lyt.addWidget(title)
        lyt.addWidget(score_lbl)
        
        # Click to switch
        btn.mousePressEvent = lambda e, gid=game_id: self.switch_game(gid)
        return btn

    def switch_game(self, game_id):
        if game_id == "snake_game": self.stack.setCurrentWidget(self.snake_game)
        elif game_id == "dodge_game": self.stack.setCurrentWidget(self.dodge_game)
        elif game_id == "memory_game": self.stack.setCurrentWidget(self.memory_game)

    def handle_game_over(self, game_id, score):
        improved = update_high_score(game_id, score)
        self.update_scores()

    def update_scores(self):
        # Refresh the labels
        for gid in ["snake_game", "dodge_game", "memory_game"]:
            lbl = self.findChild(CaptionLabel, f"score_{gid}")
            if lbl:
                lbl.setText(f"High Score: {get_high_score(gid)}")
