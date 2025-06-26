from PySide6 import QtCore, QtWidgets

class QTextArea(QtWidgets.QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedHeight(0)
        self.setReadOnly(True)
        self.textChanged.connect(self.triggerResize)
        self.verticalScrollBar().setDisabled(True)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    def resizeEvent(self, e):
        self.triggerResize()
    
    def eventFilter(self, obj, event):
        if obj == self.verticalScrollBar() and event.type() == QtCore.QEvent.Type.Wheel:
            event.ignore()
        return super().eventFilter(obj, event)

    def triggerResize(self):
        self.document().setTextWidth(self.viewport().width())
        margins = self.contentsMargins()
        height = int(self.document().size().height()
                   + margins.top() + margins.bottom())
        self.setFixedHeight(height)