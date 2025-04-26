import sys
import ctypes
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor

app = QApplication(sys.argv)
widget = QWidget()

# Set window flags for borderless and click-through
widget.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
widget.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation)

# Set minimum size
widget.setMinimumSize(650, 100)

# Set semi-transparency
widget.setWindowOpacity(0.5)

# Set black background
widget.setStyleSheet("background-color: black;")

# Add a label with white text
label = QLabel("Test Window")
label.setStyleSheet("color: white; font-size: 24px;")
label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
layout = QVBoxLayout()
layout.addWidget(label)
widget.setLayout(layout)

# Position window at top with 30px margin
screen = app.primaryScreen().geometry()
x = (screen.width() - widget.width()) // 2
y = 30
widget.move(x, y)

widget.show()
hwnd = widget.winId()
hwnd_int = int(hwnd)  # Convert sip.voidptr to an integer
ctypes.windll.user32.SetWindowDisplayAffinity(hwnd_int, 17)
sys.exit(app.exec())