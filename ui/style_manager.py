
class StyleManager:
    """
    Централизованное управление стилями для интерфейса Vision Metrics.
    Содержит цветовые схемы, CSS-строки и общие параметры оформления.
    """

    # --- ПАЛИТРА ЦВЕТОВ (macOS Finder Dark) ---
    BG_DARK = "#191919"         # Фон основного контента
    BG_PANEL = "#212121"        # Фон боковых панелей (Sidebar style)
    BG_CARD = "#2D2D2D"         # Фон внутренних карточек
    BORDER_PANEL = "#333333"    # Деликатные границы
    BORDER_CARD = "#3A3A3A"     # Границы внутренних элементов
    
    ACCENT = "#007AFF"          # macOS System Blue
    ACCENT_HOVER = "#3593FF"
    
    TEXT_PRIMARY = "#FFFFFF"    # Чисто белый для заголовков
    TEXT_SECONDARY = "#A1A1A1"  # Серый для вторичного текста
    TEXT_MUTED = "#666666"      # Глухой серый
    
    SUCCESS_BG = "#2E3A2E"      # Приглушенный темно-зеленый
    SUCCESS_TEXT = "#34C759"    # Яркий, но тонкий зеленый
    
    DANGER_BG = "#3D2B2B"       # Приглушенный темно-красный
    DANGER_TEXT = "#FF3B30"     # Системный красный
    
    WARNING_BG = "#3D352B"      # Приглушенный темно-оранжевый
    WARNING_TEXT = "#FF9F0A"    # Системный оранжевый
    
    # Специфические цвета для JSON (Syntax Highlighting)
    JSON_KEY = "#A5D6FF"
    JSON_STRING = "#A7C080"
    JSON_LITERAL = "#D2A8FF"
    JSON_TEXT = "#D1D9E0"

    # --- ГЛОБАЛЬНЫЕ СТИЛИ ---
    
    MAIN_WINDOW = f"""
        QMainWindow {{
            background-color: {BG_DARK};
            font-family: '.AppleSystemUIFont', 'SF Pro', 'Helvetica Neue', Arial;
        }}
        QTabWidget::pane {{
            border: none;
            background-color: {BG_DARK};
        }}
        QTabBar::tab {{
            background-color: rgba(255, 255, 255, 0.05);
            color: {TEXT_SECONDARY};
            padding: 6px 16px;
            margin: 4px 2px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
        }}
        QTabBar::tab:selected {{
            background-color: rgba(255, 255, 255, 0.15);
            color: white;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: rgba(255, 255, 255, 0.1);
            color: {TEXT_PRIMARY};
        }}
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 8px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(255, 255, 255, 0.15);
            min-height: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: rgba(255, 255, 255, 0.25);
        }}
    """

    # Стиль контейнера боковой панели (RegionsPanel, StatsPanel)
    PANEL_CONTAINER = f"""
        QFrame {{
            background-color: {BG_PANEL};
            border: none;
            border-radius: 12px;
        }}
    """

    # Единый заголовок для всех панелей
    PANEL_HEADER = f"""
        QLabel {{
            background-color: transparent;
            color: {TEXT_PRIMARY};
            font-weight: 700;
            font-size: 13px;
            padding: 10px 12px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            letter-spacing: 0.5px;
        }}
    """

    # Кнопки действий (основные)
    ACTION_BUTTON = f"""
        QPushButton {{
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_CARD};
            border-radius: 8px;
            padding: 5px 12px;
            background-color: {BG_CARD};
            font-weight: 400;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {BORDER_PANEL};
        }}
        QPushButton:pressed {{
            background-color: #111111;
        }}
        QPushButton:checked {{
            background-color: {ACCENT};
            border: none;
            color: white;
        }}
    """

    # Кнопки удаления/опасных действий
    DANGER_BUTTON = f"""
        QPushButton {{
            color: {DANGER_TEXT};
            border: 1px solid {DANGER_BG};
            border-radius: 6px;
            padding: 4px 10px;
            background-color: transparent;
            font-weight: 400;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {DANGER_BG};
        }}
        QPushButton:pressed {{
            background-color: #F87171;
            color: white;
        }}
    """

    # Списки (QListWidget)
    LIST_WIDGET = f"""
        QListWidget {{
            background-color: #111111;
            border: 1px solid {BORDER_PANEL};
            border-radius: 10px;
            color: {TEXT_PRIMARY};
            font-size: 13px;
            padding: 4px;
        }}
        QListWidget::item {{
            padding: 8px;
            border-radius: 6px;
            margin: 1px 0px;
        }}
        QListWidget::item:selected {{
            background-color: {ACCENT};
            color: white;
        }}
        QListWidget::item:hover:!selected {{
            background-color: rgba(255, 255, 255, 0.05);
        }}
    """

    # Таблицы (QTableWidget)
    TABLE_WIDGET = f"""
        QTableWidget {{
            background-color: transparent;
            border: none;
            color: {TEXT_PRIMARY};
            font-size: 13px;
            gridline-color: transparent;
        }}
        QHeaderView::section {{
            background-color: transparent;
            color: {TEXT_MUTED};
            padding: 8px;
            border: none;
            border-bottom: 1px solid {BORDER_PANEL};
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
        }}
        QTableWidget::item {{
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        }}
        QTableWidget::item:selected {{
            background-color: {ACCENT};
            color: white;
        }}
    """

    # Инспектор JSON (Текстовое поле)
    JSON_VIEWER = f"""
        QTextEdit {{
            background-color: {BG_DARK};
            color: {JSON_TEXT};
            font-family: 'SF Mono', Menlo, Monaco, Consolas, 'Courier New', monospace;
            font-size: 13px;
            border: none;
            padding: 10px;
        }}
    """

    # Монитор ресурсов
    RESOURCE_MONITOR = f"""
        #resource_panel {{
            background-color: {BG_PANEL};
            border-bottom: 1px solid {BORDER_PANEL};
            border-radius: 10px;
        }}
        QLabel {{
            color: {TEXT_PRIMARY};
            font-size: 12px;
        }}
        #title {{ font-weight: 600; color: {TEXT_MUTED}; text-transform: uppercase; font-size: 10px; }}
        #value {{ font-weight: 700; color: {TEXT_PRIMARY}; min-width: 45px; }}
    """

    PROGRESS_BAR = f"""
        QProgressBar {{ background-color: rgba(255, 255, 255, 0.1); border-radius: 10px; border: none; text-align: center; color: transparent; }}
        QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 10px; }}
    """

    PROGRESS_BAR_DANGER = f"""
        QProgressBar {{ background-color: rgba(255, 255, 255, 0.1); border-radius: 10px; border: none; text-align: center; color: transparent; }}
        QProgressBar::chunk {{ background-color: {DANGER_TEXT}; border-radius: 10px; }}
    """

    SLIDER_MINIMAL = f"""
        QSlider::groove:horizontal {{
            border: 0px;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: #EAEAEA;
            border: 1px solid rgba(0, 0, 0, 0.3);
            width: 20px;
            height: 20px;
            margin: -7px 0;
            border-radius: 10px;
        }}
        QSlider::sub-page:horizontal {{
            background: {ACCENT};
        }}
    """

    ENGINE_STATUS = f"""
        QWidget#engineInfo {{
            background-color: rgba(255, 255, 255, 0.05);
            border: none;
            border-radius: 8px;
        }}
        QLabel {{
            color: {TEXT_SECONDARY};
            font-size: 11px;
            font-weight: 500;
        }}
        QLabel#val {{
            color: white;
            font-weight: 700;
        }}
    """

    # --- ПАРАМЕТРЫ ДЛЯ ВИДЕО ПАНЕЛИ ---
    VIDEO_TIME_LABEL = f"color: {TEXT_SECONDARY}; font-family: 'SF Mono', 'Menlo', monospace; font-size: 11px; min-width: 80px;"
    VIDEO_CHECKBOX = f"color: {TEXT_SECONDARY}; font-weight: 500; font-size: 11px; padding: 4px;"
    VIDEO_CHECKBOX_ACTIVE = f"color: {WARNING_TEXT}; font-weight: 700; font-size: 11px; padding: 4px;"
    VIDEO_HINT = f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 400;"
    VIDEO_HINT_ACTIVE = f"color: {WARNING_TEXT}; font-size: 11px; font-weight: bold;"
