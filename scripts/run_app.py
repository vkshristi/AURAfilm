import sys
from PySide6 import QtWidgets
from aurafilm.ui.app import MainWindow   # <-- changed

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow(camera_index=0)
    w.resize(1280, 720)
    w.show()
    sys.exit(app.exec())
