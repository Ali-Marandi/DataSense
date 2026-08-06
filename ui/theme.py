"""Dark and light design system applied through a single Qt stylesheet."""
from __future__ import annotations

DARK = {
    "bg": "#0f1620",
    "surface": "#16202c",
    "surface2": "#1d2937",
    "border": "#26364a",
    "text": "#e7eef7",
    "muted": "#93a4b8",
    "primary": "#2dd4bf",
    "primary_dark": "#14b8a6",
    "on_primary": "#04211f",
    "accent": "#7dd3fc",
    "danger": "#f87171",
    "grid": "#22303f",
}

LIGHT = {
    "bg": "#f4f7fa",
    "surface": "#ffffff",
    "surface2": "#eef3f8",
    "border": "#d7e0ea",
    "text": "#16202f",
    "muted": "#5c6b80",
    "primary": "#0f9488",
    "primary_dark": "#0b7a70",
    "on_primary": "#ffffff",
    "accent": "#0369a1",
    "danger": "#dc2626",
    "grid": "#e3eaf2",
}

_TEMPLATE = """
* {{ font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; }}
QWidget {{ background: {bg}; color: {text}; }}
QMainWindow::separator {{ background: {border}; width: 1px; height: 1px; }}

QToolBar {{ background: {surface}; border-bottom: 1px solid {border}; padding: 6px 10px; spacing: 6px; }}
QToolBar QToolButton {{ padding: 7px 12px; border-radius: 8px; color: {text}; }}
QToolBar QToolButton:hover {{ background: {surface2}; }}
QToolBar QToolButton:pressed {{ background: {primary_dark}; color: {on_primary}; }}

QMenuBar {{ background: {surface}; border-bottom: 1px solid {border}; }}
QMenuBar::item {{ padding: 7px 12px; background: transparent; }}
QMenuBar::item:selected {{ background: {surface2}; border-radius: 6px; }}
QMenu {{ background: {surface}; border: 1px solid {border}; padding: 6px; border-radius: 10px; }}
QMenu::item {{ padding: 7px 22px 7px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {primary_dark}; color: {on_primary}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 5px 6px; }}

QTabWidget::pane {{ border: 1px solid {border}; border-radius: 12px; background: {surface}; top: -1px; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{ background: transparent; color: {muted}; padding: 10px 20px; margin-right: 4px;
    border-top-left-radius: 10px; border-top-right-radius: 10px; font-weight: 600; }}
QTabBar::tab:hover {{ color: {text}; }}
QTabBar::tab:selected {{ background: {surface}; color: {primary}; border: 1px solid {border};
    border-bottom-color: {surface}; }}

QGroupBox {{ background: {surface}; border: 1px solid {border}; border-radius: 12px;
    margin-top: 16px; padding: 14px 12px 12px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 2px 8px; color: {primary};
    background: transparent; text-transform: uppercase; font-size: 11px; letter-spacing: .08em; }}

QPushButton {{ background: {surface2}; border: 1px solid {border}; border-radius: 9px;
    padding: 8px 16px; color: {text}; font-weight: 600; }}
QPushButton:hover {{ border-color: {primary}; color: {primary}; }}
QPushButton:pressed {{ background: {border}; }}
QPushButton:disabled {{ color: {muted}; border-color: {border}; background: {surface}; }}
QPushButton[accent="true"] {{ background: {primary}; border: none; color: {on_primary}; }}
QPushButton[accent="true"]:hover {{ background: {primary_dark}; color: {on_primary}; }}
QPushButton[danger="true"] {{ border-color: {danger}; color: {danger}; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {surface2}; border: 1px solid {border}; border-radius: 8px; padding: 7px 10px;
    selection-background-color: {primary_dark}; selection-color: {on_primary}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {{
    border-color: {primary}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {surface}; border: 1px solid {border};
    selection-background-color: {primary_dark}; selection-color: {on_primary}; outline: none; }}

QListWidget, QTreeWidget, QTableView {{ background: {surface}; border: 1px solid {border};
    border-radius: 10px; alternate-background-color: {surface2}; gridline-color: {grid}; }}
QListWidget::item, QTreeWidget::item {{ padding: 6px 8px; border-radius: 6px; }}
QListWidget::item:selected, QTreeWidget::item:selected, QTableView::item:selected {{
    background: {primary_dark}; color: {on_primary}; }}
QHeaderView::section {{ background: {surface2}; color: {muted}; border: none;
    border-right: 1px solid {border}; border-bottom: 1px solid {border}; padding: 8px 10px;
    font-weight: 600; }}
QTableCornerButton::section {{ background: {surface2}; border: none; }}

QScrollBar:vertical {{ background: transparent; width: 11px; margin: 4px; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 4px; }}
QScrollBar::handle {{ background: {border}; border-radius: 5px; min-height: 30px; min-width: 30px; }}
QScrollBar::handle:hover {{ background: {primary_dark}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    background: none; border: none; height: 0; width: 0; }}

QStatusBar {{ background: {surface}; border-top: 1px solid {border}; color: {muted}; }}
QStatusBar QLabel {{ color: {muted}; padding: 0 8px; }}
QProgressBar {{ background: {surface2}; border: 1px solid {border}; border-radius: 8px;
    height: 8px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {primary}; border-radius: 8px; }}
QSplitter::handle {{ background: {border}; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid {border}; background: {surface2}; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {primary};
    border-color: {primary}; }}
QToolTip {{ background: {surface2}; color: {text}; border: 1px solid {primary};
    border-radius: 6px; padding: 6px 8px; }}
QLabel[role="title"] {{ font-size: 20px; font-weight: 700; }}
QLabel[role="subtitle"] {{ color: {muted}; font-size: 12px; }}
QLabel[role="kpi"] {{ background: {surface2}; border: 1px solid {border}; border-radius: 12px;
    padding: 14px 16px; font-size: 13px; }}
"""


def palette(dark: bool = True) -> dict[str, str]:
    return DARK if dark else LIGHT


def stylesheet(dark: bool = True) -> str:
    return _TEMPLATE.format(**palette(dark))
