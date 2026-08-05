import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from qt_material import apply_stylesheet

def main():
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    
    # Apply a modern dark theme
    apply_stylesheet(app, theme='dark_teal.xml')
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
