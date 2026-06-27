"""Application entry point."""
import sys
from PyQt6.QtWidgets import QApplication

from pbi_bgdesign.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    # Check for command line argument (Power BI external tool)
    if len(sys.argv) > 1:
        pbix_path = sys.argv[1]
        window.load_pbix(pbix_path)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
