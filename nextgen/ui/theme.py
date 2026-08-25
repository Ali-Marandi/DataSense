DARK_STYLESHEET = """
QWidget {
    background: #0b1220;
    color: #e7edf8;
    font-family: "Segoe UI", "Noto Sans", Arial, sans-serif;
    font-size: 13px;
}
QMainWindow::separator { background: #24314a; width: 1px; height: 1px; }
QToolBar {
    background: #101a2c;
    border: none;
    border-bottom: 1px solid #25334d;
    spacing: 6px;
    padding: 8px 12px;
}
QToolButton, QPushButton {
    background: #1d4ed8;
    border: 1px solid #3168ef;
    border-radius: 8px;
    color: #ffffff;
    padding: 8px 12px;
    font-weight: 600;
}
QToolButton:hover, QPushButton:hover { background: #2a61eb; border-color: #76a1ff; }
QToolButton:pressed, QPushButton:pressed { background: #163cab; }
QFrame#card, QFrame#metricCard {
    background: #121e31;
    border: 1px solid #263854;
    border-radius: 12px;
}
QFrame#dashboardHero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #152949, stop:1 #16223b);
    border: 1px solid #35517a;
    border-radius: 14px;
}
QLabel#navBrand { font-size: 24px; font-weight: 750; color: #f5f8ff; }
QLabel#navFooter { color: #91a3bf; font-size: 11px; letter-spacing: 0.5px; }
QPushButton#navButton {
    text-align: left;
    background: transparent;
    border: 1px solid transparent;
    color: #b9c8df;
    padding: 10px 11px;
}
QPushButton#navButton:hover { background: #172842; border-color: #284364; color: #ffffff; }
QPushButton#navButton[active="true"] { background: #1d4ed8; border-color: #6c9cff; color: white; }
QLabel#pageHeading { font-size: 28px; font-weight: 750; color: #f4f7ff; }
QLabel#dashboardHeading { font-size: 25px; font-weight: 750; color: #f4f7ff; }
QLabel#muted, QLabel#metricDetail { color: #9bacc6; }
QLabel#sourceLabel { color: #b8d1ff; font-weight: 600; margin-top: 6px; }
QLabel#trustBadge {
    background: #26344b;
    border: 1px solid #496381;
    border-radius: 12px;
    color: #d3e0f5;
    font-size: 13px;
    font-weight: 750;
    padding: 12px;
}
QLabel#trustBadge[state="approved"] { background: #0f3b36; border-color: #32b598; color: #91f0d9; }
QLabel#trustBadge[state="blocked"] { background: #4a2027; border-color: #d65e6c; color: #ffbec5; }
QLabel#trustBadge[state="pending"] { background: #28364a; border-color: #5a769b; color: #c0d6f1; }
QLabel#metricTitle, QLabel#sectionTitle { color: #9eafc9; font-size: 11px; font-weight: 700; letter-spacing: 1.1px; }
QLabel#metricValue { color: #f5f8ff; font-size: 28px; font-weight: 750; padding-top: 4px; }
QLabel#datasetStatus, QLabel#qualitySummary {
    background: #0f1b2c;
    border: 1px solid #263854;
    border-radius: 8px;
    color: #cbd9ed;
    padding: 10px;
}
QTextEdit {
    background: #0e1727;
    border: 1px solid #2a3b57;
    border-radius: 8px;
    color: #dce7f6;
    padding: 8px;
    selection-background-color: #315fb1;
}
QTableWidget {
    background: #0e1727;
    alternate-background-color: #101d31;
    border: 1px solid #2a3b57;
    border-radius: 8px;
    gridline-color: #263854;
    color: #dce7f6;
    selection-background-color: #244d92;
    selection-color: #ffffff;
}
QHeaderView::section {
    background: #17253a;
    border: none;
    border-bottom: 1px solid #2b3e5d;
    color: #9fb3d2;
    font-weight: 700;
    padding: 8px;
}
QTableCornerButton::section { background: #17253a; border: none; }
QProgressBar {
    background: #0b1524;
    border: 1px solid #314866;
    border-radius: 7px;
    color: #dce7f6;
    min-height: 18px;
    text-align: center;
}
QProgressBar::chunk { background: #1fa889; border-radius: 6px; }
QStatusBar { background: #101a2c; border-top: 1px solid #25334d; color: #9eb1cb; }
"""
