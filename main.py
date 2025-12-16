"""
Matrix Lab - A Node-Based Visual Computing Environment for Linear Algebra

Entry point for the application.
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from view.main_window import MainWindow


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Set application details
    app.setApplicationName("Matrix Lab")
    app.setOrganizationName("MatrixLab")
    
    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
