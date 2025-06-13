import os
import sys
import string
import inspect
import json
from PySide6 import QtCore, QtWidgets, QtGui

# copied from the tests and slightly edited. probably not the beeessssst... but it works!
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
newdir = os.path.dirname(currentdir)
newdir = os.path.join(newdir, "api")
sys.path.insert(0, newdir)

from scalar.client.client import Client


ALLOWED_NAME_CHARACTERS = string.ascii_letters+string.digits+"_-."


class Settings:
    current_theme: str
    name: str
    last_server_ip: str
    last_server_port: int
    
    def __init__(self):
        self.load()
    
    # loads the settings
    def load(self):
        print("loading settings...")
        
        if not os.path.isfile("data/settings.json"):
            os.makedirs("data", exist_ok=True) # exist, okay?
            with open("data/settings.json", "w") as file:
                file.write("{}")
        
        with open("data/settings.json", "r") as file:
            data = json.load(file)
        
        self.current_theme    = data.get("current_theme", "default_dark.css")
        self.name             = data.get("name", "")
        self.last_server_ip   = data.get("last_server_ip", "")
        self.last_server_port = data.get("last_server_port", -1)
        
        self.save()

    # saves the settings
    def save(self):
        print("saving settings...")
        
        data = {}
        
        data["current_theme"]    = self.current_theme
        data["name"]             = self.name
        data["last_server_ip"]   = self.last_server_ip
        data["last_server_port"] = self.last_server_port
        
        with open("data/settings.json", "w") as file:
            json.dump(data, file)
    
    # resets the settings
    def reset(self):
        print("resetting settings...")
        
        with open("data/settings.json", "w") as file:
            file.write("{}")
        
        self.load()

settings: Settings = Settings()


# the main window
# please do not the MainWindow
# due to the g-globals (:fearful:), there can only be ONE MainWindow in a process
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.resize(1200, 800)
        
        self.reload_theme()
        
        self.setWindowTitle("Scalar - Not connected")
        
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)

        self.main_layout = QtWidgets.QHBoxLayout()
        main_widget.setLayout(self.main_layout)
        
        # the menu bar
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
    
    # adds the left frames, with the channel list and name text box
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
        self.name_text_box.setPlaceholderText("your_name")
        self.name_text_box.setMaxLength(50)
        self.name_text_box.textEdited.connect(self.name_edited)
        you_frame_layout.addWidget(self.name_text_box)

    # adds the middle frame, with the messages and message box
    def add_middle_frame(self):
        middle_frame = QtWidgets.QFrame()
        middle_frame.setObjectName("middle_frame")
        self.main_layout.addWidget(middle_frame)
        
        middle_frame_layout = QtWidgets.QVBoxLayout()
        middle_frame.setLayout(middle_frame_layout)
        
        self.messages = QtWidgets.QScrollArea()
        middle_frame_layout.addWidget(self.messages)
        
        messages_widget = QtWidgets.QWidget()
        #messages_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.messages.setWidget(messages_widget)
        
        messages_layout = QtWidgets.QVBoxLayout()
        messages_widget.setLayout(messages_layout)
        
        lable = QtWidgets.QLabel("Testing123")
        #lable.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        messages_layout.addWidget(lable)
        
        self.message_box = QtWidgets.QTextEdit()
        self.message_box.setMaximumHeight(100)
        self.message_box.setPlaceholderText("Message")
        self.message_box.setAcceptRichText(False)
        self.message_box.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.message_box.textChanged.connect(self.message_box_changed)
        middle_frame_layout.addWidget(self.message_box)

    # adds the right frame, with the connected user list and user info
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
        self.user_info.setVisible(False)
        frame_layout.addWidget(self.user_info)
    
    # reloads the theme
    def reload_theme(self):
        if settings.current_theme == "":
            self.setStyleSheet("")
            return
        if os.path.isfile("themes/" + settings.current_theme):
            theme_file = open("themes/" + settings.current_theme)
            self.setStyleSheet(theme_file.read())
            theme_file.close()
    
    # adds a message to the message display
    def add_message(self, who: str, message: str):
        text = "<" + who + "> " + message
        print(text)
        # TODO: add the message to the message display
    
    @QtCore.Slot()
    def about(self):
        print("about")
    
    @QtCore.Slot()
    def open_settings(self):
        print("open settings")
    
    @QtCore.Slot()
    def connect(self):
        text = settings.last_server_ip
        if settings.last_server_port >= 0:
            text += ":" + str(settings.last_server_port)
        text, ok = QtWidgets.QInputDialog.getText(self, "Connect", "Connect to:", QtWidgets.QLineEdit.EchoMode.Normal, text)
        if ok: # my favorite line
            parts = text.split(":")
            if len(parts) != 2:
                message_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Warning, "Bad", "Bad", QtWidgets.QMessageBox.StandardButton.Ok, self)
                message_box.exec()
                return
            ip = parts[0]
            if ip == "":
                message_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Warning, "Bad", "Bad IP", QtWidgets.QMessageBox.StandardButton.Ok, self)
                message_box.exec()
                return
            try:
                port = int(parts[1])
                if port < 0 or port > 65535:
                    message_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Warning, "Bad", "Bad port not in range", QtWidgets.QMessageBox.StandardButton.Ok, self)
                    message_box.exec()
                    return
            except ValueError:
                message_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Warning, "Bad", "Bad port", QtWidgets.QMessageBox.StandardButton.Ok, self)
                message_box.exec()
                return
            settings.last_server_ip = ip
            settings.last_server_port = port
            settings.save()
            self.server_menu.actions()[0].setEnabled(False)
            self.server_menu.actions()[1].setEnabled(True)
            self.server_menu.actions()[2].setEnabled(True)
            self.name_text_box.setEnabled(False)
            message_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.NoIcon, "Connected", f"Connected to {ip} with port {port}", QtWidgets.QMessageBox.StandardButton.Ok, self)
            message_box.exec()
    
    @QtCore.Slot()
    def disconnect(self):
        self.server_menu.actions()[0].setEnabled(True)
        self.server_menu.actions()[1].setEnabled(False)
        self.server_menu.actions()[2].setEnabled(False)
        self.name_text_box.setEnabled(True)
    
    @QtCore.Slot()
    def reconnect(self):
        print("reconnect")
    
    @QtCore.Slot()
    def toggle_user_list(self):
        self.right_frame.setVisible(not self.right_frame.isVisible())
    
    @QtCore.Slot()
    def name_edited(self):
        # make sure you are not using bad characters
        name = self.name_text_box.text()
        cursor_position = self.name_text_box.cursorPosition()
        i = 0
        while i < len(name):
            if name[i] not in ALLOWED_NAME_CHARACTERS:
                name = name[:i] + name[i+1:] # couldn't think of another way of removing a specific character at an index from a string
                cursor_position -= 1
                i -= 1
            i += 1
        if name != self.name_text_box.text():
            self.name_text_box.setText(name)
            self.name_text_box.setCursorPosition(cursor_position)
        else:
            print(name)
            settings.name = name
            settings.save()
    
    @QtCore.Slot()
    def message_box_changed(self):
        message = self.message_box.toPlainText()
        self.add_message(settings.name, message)
