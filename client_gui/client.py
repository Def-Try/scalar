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
    theme: str
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
        
        self.theme            = data.get("theme", "default_dark.css")
        self.name             = data.get("name", "")
        self.last_server_ip   = data.get("last_server_ip", "")
        self.last_server_port = data.get("last_server_port", -1)
        
        self.save()

    # saves the settings
    def save(self):
        print("saving settings...")
        
        data = {}
        
        data["theme"]            = self.theme
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


# the main window class
# please do not the MainWindow
# due to the g-globals (:fearful:), there can only be ONE MainWindow in a process
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.resize(1200, 800)
        
        self.reload_theme()
        
        self.setWindowTitle("Scalar")
        
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)

        self.main_layout = QtWidgets.QHBoxLayout()
        main_widget.setLayout(self.main_layout)
        
        # the menu bar
        menu_bar = QtWidgets.QMenuBar()
        self.file_menu = menu_bar.addMenu("File")
        self.file_menu.addAction(QtGui.QAction("About", self, triggered=self._about))
        self.file_menu.addAction(QtGui.QAction("Settings", self, triggered=self._open_settings))
        self.file_menu.addAction(QtGui.QAction("Quit", self, triggered=self.close))
        self.server_menu = menu_bar.addMenu("Server")
        self.server_menu.addAction(QtGui.QAction("Connect", self, triggered=self._connect))
        self.server_menu.addAction(QtGui.QAction("Disconnect", self, triggered=self._disconnect))
        self.server_menu.actions()[1].setEnabled(False) # Server/Disconnect
        self.view_menu = menu_bar.addMenu("View")
        self.view_menu.addAction(QtGui.QAction("View users", self, triggered=self._toggle_user_list))
        self.view_menu.addAction(QtGui.QAction("Reload theme", self, triggered=self.reload_theme))
        self.main_layout.setMenuBar(menu_bar)
        
        self.add_left_frames()
        self.add_middle_frame()
        self.add_right_frame()
    
        self.update_from_settings()
        
        self.channels = {"main": [["message with no name tag"], ["message", "i am with a name tag"], ["testing", "testing123"]]}
        self.current_channel = "main"
        
        self.update_messages()
    
    # adds the left frames, with the channel list and name text box
    def add_left_frames(self):
        # the widget that contains both of the frames
        widget = QtWidgets.QWidget()
        widget.setMinimumWidth(100)
        widget.setMaximumWidth(250)
        self.main_layout.addWidget(widget)
        
        widget_layout = QtWidgets.QVBoxLayout()
        widget_layout.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))
        widget.setLayout(widget_layout)
        
        # the top frame with the channel list
        channel_list_frame = QtWidgets.QFrame()
        channel_list_frame.setObjectName("channel_list_frame")
        widget_layout.addWidget(channel_list_frame)
        
        channel_list_frame_layout = QtWidgets.QVBoxLayout()
        channel_list_frame.setLayout(channel_list_frame_layout)
        
        channel_list_frame_layout.addWidget(QtWidgets.QLabel("Channels"))
        
        # the list with all the channels
        self.channel_list = QtWidgets.QListWidget()
        channel_list_frame_layout.addWidget(self.channel_list)
        
        # the bottom frame with the users name
        you_frame = QtWidgets.QFrame()
        you_frame.setObjectName("you_frame")
        widget_layout.addWidget(you_frame)
        
        you_frame_layout = QtWidgets.QVBoxLayout()
        you_frame.setLayout(you_frame_layout)
        
        # the text box where the user can edit their name
        self.name_text_box = QtWidgets.QLineEdit()
        self.name_text_box.setPlaceholderText("your_name")
        self.name_text_box.setMaxLength(50)
        self.name_text_box.textEdited.connect(self._name_edited)
        you_frame_layout.addWidget(self.name_text_box)

    # adds the middle frame, with the messages and message box
    def add_middle_frame(self):
        # the frame
        middle_frame = QtWidgets.QFrame()
        middle_frame.setObjectName("middle_frame")
        self.main_layout.addWidget(middle_frame)
        
        middle_frame_layout = QtWidgets.QVBoxLayout()
        middle_frame.setLayout(middle_frame_layout)
        
        # the message display
        # # doesnt work, even though
        # self.messages = QtWidgets.QScrollArea()
        # middle_frame_layout.addWidget(self.messages)
        
        # messages_label = QtWidgets.QLabel("why does this not work!!!")
        # messages_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignBottom)
        # self.messages.setWidget(messages_label)
        
        # works but broken with a lot of messages
        self.messages = QtWidgets.QLabel()
        self.messages.setAlignment(QtCore.Qt.AlignmentFlag.AlignBottom)
        middle_frame_layout.addWidget(self.messages)
        
        # the message textbox
        self.message_box = QtWidgets.QTextEdit()
        self.message_box.setMaximumHeight(100)
        self.message_box.setPlaceholderText("Message")
        self.message_box.setAcceptRichText(False)
        self.message_box.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.message_box.textChanged.connect(self._message_box_changed)
        middle_frame_layout.addWidget(self.message_box)

    # adds the right frame, with the connected user list and user info
    def add_right_frame(self):
        # the frame
        self.right_frame = QtWidgets.QFrame()
        self.right_frame.setObjectName("right_frame")
        self.right_frame.setMinimumWidth(100)
        self.right_frame.setMaximumWidth(250)
        self.main_layout.addWidget(self.right_frame)
        
        frame_layout = QtWidgets.QVBoxLayout()
        self.right_frame.setLayout(frame_layout)
        
        frame_layout.addWidget(QtWidgets.QLabel("Connected Users"))
        
        # the list with all the connected users
        self.user_list = QtWidgets.QListWidget()
        frame_layout.addWidget(self.user_list)
        
        self.user_info = QtWidgets.QLabel("Name:\nFingerprint:")
        self.user_info.setObjectName("user_info")
        self.user_info.setVisible(False)
        frame_layout.addWidget(self.user_info)
    
    def connect(self, ip: str, port: int):
        print(f"connecting to {ip} with port {port}")
        
        # TODO: connect to server
        
        # enable and disable some menubar buttons
        self.server_menu.actions()[0].setEnabled(False) # Server/Connect
        self.server_menu.actions()[1].setEnabled(True)  # Server/Disconnect
        self.name_text_box.setEnabled(False)
    
    def disconnect(self, ):
        print("disconnecting")
        
        # TODO: disconnect from server
        
        # enable and disable some menubar buttons
        self.server_menu.actions()[0].setEnabled(True)  # Server/Connect
        self.server_menu.actions()[1].setEnabled(False) # Server/Disconnect
        self.name_text_box.setEnabled(True)
    
    # reloads the theme
    def reload_theme(self):
        if settings.theme == "":
            self.setStyleSheet("")
            return
        if os.path.isfile("themes/" + settings.theme):
            theme_file = open("themes/" + settings.theme)
            self.setStyleSheet(theme_file.read())
            theme_file.close()
    
    # updates things from the settings
    def update_from_settings(self):
            self.name_text_box.setText(settings.name)
    
    # updates the messages
    def update_messages(self):
        text = ""
        for message in self.channels[self.current_channel]:
            text += "\n"
            if len(message) == 1:
                text += message[0]
            elif len(message) == 2:
                text += "<" + message[0] + "> " + message[1]
        # self.messages.widget().setText(text) # for the QScrollArea version
        self.messages.setText(text)
    
    # adds a message to the message display
    def add_message(self, channel: str, who: str, message: str):
        text = message
        print("<" + who + "> " + text)
        self.channels[channel].append([who, text])
        self.update_messages()
    
    def show_info(self, title: str, message: str):
        message_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.NoIcon, title, message, QtWidgets.QMessageBox.StandardButton.Ok, self)
        message_box.exec()
    
    def show_warn(self, title: str, message: str):
        message_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Warning, title, message, QtWidgets.QMessageBox.StandardButton.Ok, self)
        message_box.exec()
    
    @QtCore.Slot()
    def _about(self):
        print("about")
        # TODO: add about dialog
    
    @QtCore.Slot()
    def _open_settings(self):
        print("open settings")
        # TODO: add settings dialog
    
    @QtCore.Slot()
    def _connect(self):
        # setup the text for the text box from whatever you wrote last
        text = settings.last_server_ip
        if settings.last_server_port >= 0:
            text += ":" + str(settings.last_server_port)
            
        # show the dialog
        text, ok = QtWidgets.QInputDialog.getText(self, "Connect", "Connect to:", QtWidgets.QLineEdit.EchoMode.Normal, text)
        if not ok:
            return

        parts = text.split(":")
        # give an "error" if you dont include the port
        # TODO: make it not needed with a default port
        if len(parts) != 2:
            self.show_warn("Bad", "Bad")
            return
        
        # get the ip from the combined ip and port, and check if its not empty somehow
        ip = parts[0]
        if ip == "":
            self.show_warn("Bad", "Bad IP")
            return

        # try to get the port from the combined ip and port as an int
        try:
            port = int(parts[1])
            # remember, a port cannot be negative or above 65535 (unsigned 16 bit int limit)
            if port < 0 or port > 65535:
                self.show_warn("Bad", "Bad port, not in range")
                return
        # that is not an int
        except ValueError:
            self.show_warn("Bad", "Bad port")
            return

        # remember the ip and port
        settings.last_server_ip = ip
        settings.last_server_port = port
        
        self.connect(ip, port)
        
        self.show_info("Connected", f"Connected to {ip} with port {port}")
    
    @QtCore.Slot()
    def _disconnect(self):
        self.disconnect()
    
    @QtCore.Slot()
    def _toggle_user_list(self):
        self.right_frame.setVisible(not self.right_frame.isVisible())
    
    @QtCore.Slot()
    def _name_edited(self):
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
        
        # check if it actually changed (textEdited would still trigger the signal if you wrote a disallowed character)
        if name != self.name_text_box.text():
            self.name_text_box.setText(name)
            self.name_text_box.setCursorPosition(cursor_position)
        else:
            settings.name = name
    
    @QtCore.Slot()
    def _message_box_changed(self):
        # make sure it doesnt give an error, because editing a QTextEdit counts as changing it
        if self.message_box.toPlainText() == "":
            return
        
        # check if the last character is a new line (basically check for pressing enter), and then send the message without the new line
        if self.message_box.toPlainText()[-1] == "\n":
            message = self.message_box.toPlainText()[:-1]
            self.add_message(self.current_channel, settings.name, message)
            self.message_box.setText("")
    
    def closeEvent(self, event: QtGui.QCloseEvent):
        settings.save()
        event.accept()
