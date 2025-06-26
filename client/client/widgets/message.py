from PySide6 import QtCore, QtWidgets

from .textarea import QTextArea

class GUI_Message(QtWidgets.QWidget):
    layout: QtWidgets.QHBoxLayout
    widget_name: QtWidgets.QLabel
    widget_text: QTextArea

    def __init__(self, author_name: str, text_content: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.layout = QtWidgets.QHBoxLayout()
        
        self.widget_name = QtWidgets.QLabel(
            f"<{author_name}>",
            alignment=QtCore.Qt.AlignmentFlag.AlignTop
        )

        self.widget_text = QTextArea(
            text_content
        )
        self.widget_text.setContentsMargins(0, 0, 0, 0)
        self.widget_text.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.widget_text.document().setTextWidth(self.widget_text.viewport().width())

        self.widget_name.adjustSize()
        self.widget_text.adjustSize()

        self.layout.addWidget(self.widget_name)
        self.layout.addWidget(self.widget_text)

        self.setLayout(self.layout)
