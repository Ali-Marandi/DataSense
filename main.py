import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from qt_material import apply_stylesheet

def main():
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    
    # Apply a professional dark theme with custom styling
    extra = {
        'density_scale': '-1',
        'danger': '#dc3545',
        'warning': '#ffc107',
        'success': '#28a745',
    }
    apply_stylesheet(app, theme='dark_teal.xml', extra=extra)
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
