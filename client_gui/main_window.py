import os.path
from PySide6 import QtCore, QtWidgets, QtGui

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.current_theme = "default_dark.css"
        
        self.reload_theme()
        
        self.setWindowTitle("Scalar - Not connected")
        
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)

        self.main_layout = QtWidgets.QHBoxLayout()
        main_widget.setLayout(self.main_layout)
        
        menu_bar = QtWidgets.QMenuBar()
        self.file_menu = menu_bar.addMenu("File")
        self.file_menu.addAction(QtGui.QAction("About", self, triggered=self.about))
        self.file_menu.addAction(QtGui.QAction("Settings", self, triggered=self.open_settings))
        self.file_menu.addAction(QtGui.QAction("Quit", self, triggered=self.close))
        self.server_menu = menu_bar.addMenu("Server")
        self.server_menu.addAction(QtGui.QAction("Connect", self, triggered=self.connect))
        self.server_menu.addAction(QtGui.QAction("Disconnect", self, triggered=self.disconnect))
        self.server_menu.actions()[1].setEnabled(False)
        self.server_menu.addAction(QtGui.QAction("Reconnect", self, triggered=self.reconnect))
        self.server_menu.actions()[2].setEnabled(False)
        self.view_menu = menu_bar.addMenu("View")
        self.view_menu.addAction(QtGui.QAction("View users", self, triggered=self.toggle_user_list))
        self.view_menu.addAction(QtGui.QAction("Reload theme", self, triggered=self.reload_theme))
        self.main_layout.setMenuBar(menu_bar)
        
        self.add_left_frames()
        
        self.add_middle_frame()
    
        self.add_right_frame()
        
    def add_left_frames(self):
        widget = QtWidgets.QWidget()
        widget.setMinimumWidth(100)
        widget.setMaximumWidth(250)
        self.main_layout.addWidget(widget)
        
        widget_layout = QtWidgets.QVBoxLayout()
        widget_layout.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))
        widget.setLayout(widget_layout)
        
        channel_list_frame = QtWidgets.QFrame()
        channel_list_frame.setObjectName("channel_list_frame")
        widget_layout.addWidget(channel_list_frame)
        
        channel_list_frame_layout = QtWidgets.QVBoxLayout()
        channel_list_frame.setLayout(channel_list_frame_layout)
        
        channel_list_frame_layout.addWidget(QtWidgets.QLabel("Channels"))
        
        self.channel_list = QtWidgets.QListWidget()
        channel_list_frame_layout.addWidget(self.channel_list)
        
        you_frame = QtWidgets.QFrame()
        you_frame.setObjectName("you_frame")
        widget_layout.addWidget(you_frame)
        
        you_frame_layout = QtWidgets.QVBoxLayout()
        you_frame.setLayout(you_frame_layout)
        
        self.name_text_box = QtWidgets.QLineEdit()
        self.name_text_box.setPlaceholderText("Your name goes here")
        you_frame_layout.addWidget(self.name_text_box)

    def add_middle_frame(self):
        middle_frame = QtWidgets.QFrame()
        middle_frame.setObjectName("middle_frame")
        self.main_layout.addWidget(middle_frame)
        
        middle_frame_layout = QtWidgets.QVBoxLayout()
        middle_frame.setLayout(middle_frame_layout)
        
        self.messages = QtWidgets.QLabel()
        middle_frame_layout.addWidget(self.messages)
        
        self.message_box = QtWidgets.QTextEdit()
        self.message_box.setPlaceholderText("Message")
        self.message_box.setMaximumHeight(50)
        middle_frame_layout.addWidget(self.message_box)

    def add_right_frame(self):
        self.right_frame = QtWidgets.QFrame()
        self.right_frame.setObjectName("right_frame")
        self.right_frame.setMinimumWidth(100)
        self.right_frame.setMaximumWidth(250)
        self.main_layout.addWidget(self.right_frame)
        
        frame_layout = QtWidgets.QVBoxLayout()
        self.right_frame.setLayout(frame_layout)
        
        frame_layout.addWidget(QtWidgets.QLabel("Connected Users"))
        
        self.user_list = QtWidgets.QListWidget()
        frame_layout.addWidget(self.user_list)
        
        self.user_info = QtWidgets.QLabel("Name:\nFingerprint:")
        self.user_info.setObjectName("user_info")
        frame_layout.addWidget(self.user_info)
    
    def reload_theme(self):
        if self.current_theme == "":
            self.setStyleSheet("")
            return
        if os.path.isfile("themes/" + self.current_theme):
            theme_file = open("themes/" + self.current_theme)
            self.setStyleSheet(theme_file.read())
            theme_file.close()
    
    @QtCore.Slot()
    def about(self):
        print("about")
    
    @QtCore.Slot()
    def open_settings(self):
        print("open settings")
    
    @QtCore.Slot()
    def connect(self):
        print("connect")
        self.server_menu.actions()[0].setEnabled(False)
        self.server_menu.actions()[1].setEnabled(True)
        self.server_menu.actions()[2].setEnabled(True)
    
    @QtCore.Slot()
    def disconnect(self):
        print("disconnect")
        self.server_menu.actions()[0].setEnabled(True)
        self.server_menu.actions()[1].setEnabled(False)
        self.server_menu.actions()[2].setEnabled(False)
    
    @QtCore.Slot()
    def reconnect(self):
        print("reconnect")
    
    @QtCore.Slot()
    def toggle_user_list(self):
        self.right_frame.setVisible(not self.right_frame.isVisible())
