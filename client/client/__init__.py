
import scalar.client.implementations.scalar0 as scalar0
import scalar.primitives as primitives
import scalar.protocol.encryption as encryption

from PySide6 import QtCore, QtWidgets, QtGui
import os

from .widgets.message import GUI_Message

STATE_DISCONNECTED = 0
STATE_CONNECTED = 1

class MainWindow(QtWidgets.QMainWindow):
    # scalar0 client below
    main_widget: QtWidgets.QWidget = None
    main_layout: QtWidgets.QLayout = None

    left_widget: QtWidgets.QWidget = None
    center_widget: QtWidgets.QWidget = None
    right_widget: QtWidgets.QWidget = None
    center_stacker: QtWidgets.QStackedWidget = None

    channels: dict[int, list[int, str, QtWidgets.QWidget]] = {}

    state: int = STATE_DISCONNECTED

    def __init__(self):
        super().__init__()
        self.resize(1200, 800)
        self.setWindowTitle("Scalar")

        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_widget.setLayout(self.main_layout)

        self._init_make_menubar()
        self._init_make_lbar()
        self._init_make_cframe()
        self._init_make_rbar()

        self.add_channel(-1, "logs")
        self.select_channel(-1)

        self.add_message(-1, "INFO", "This channel will contain various client logs")

        self._init_create_client()
        self._init_load_client_data()

    def _init_load_client_data(self):
        os.makedirs('data/client', exist_ok=True)


        os.makedirs('data/client/keys', exist_ok=True)
        for keytype in encryption.SUPPORTED:
            try:
                with open(f'data/client/keys/{keytype}.priv', 'rb') as f:
                    self.client.load_key(keytype, f.read())
            except FileNotFoundError:
                self.client.generate_key(keytype)
                with open(f'data/client/keys/{keytype}.priv', 'wb') as f:
                    f.write(self.client.save_key(keytype))

    def _init_make_menubar(self):
        menu_bar = QtWidgets.QMenuBar()
        self.file_menu = menu_bar.addMenu("File")
        self.file_menu.addAction(QtGui.QAction("About", self, triggered=self._menubar_action_about))
        self.file_menu.addAction(QtGui.QAction("Settings", self, triggered=self._menubar_action_settings))
        self.file_menu.addAction(QtGui.QAction("Quit", self, triggered=self.close))
        self.server_menu = menu_bar.addMenu("Server")
        self.server_menu.addAction(QtGui.QAction("Connect", self, triggered=self._menubar_action_connect))
        self.server_menu.addAction(QtGui.QAction("Disconnect", self, triggered=self._menubar_action_disconnect, enabled=False))
        # self.server_menu.actions()[1].setEnabled(False) # Server/Disconnect
        self.view_menu = menu_bar.addMenu("View")
        # self.view_menu.addAction(QtGui.QAction("View users", self, triggered=self._menubar_action_toggle_user_list))
        # self.view_menu.addAction(QtGui.QAction("Reload theme", self, triggered=self.reload_theme))
        self.main_layout.setMenuBar(menu_bar)

    def _init_make_rbar(self):
        self.right_widget = QtWidgets.QFrame()
        self.right_widget.setObjectName("right_widget")
        self.right_widget.setMinimumWidth(100)
        self.right_widget.setMaximumWidth(250)
        self.main_layout.addWidget(self.right_widget)
        
        frame_layout = QtWidgets.QVBoxLayout()
        self.right_widget.setLayout(frame_layout)
        frame_layout.addWidget(QtWidgets.QLabel("Connected Users"))
        
        # the list with all the connected users
        self.user_list = QtWidgets.QListWidget()
        frame_layout.addWidget(self.user_list)
        
        self.user_info = QtWidgets.QLabel("Name:\nFingerprint:")
        self.user_info.setObjectName("user_info")
        self.user_info.setVisible(False)
        frame_layout.addWidget(self.user_info)

    def _init_make_lbar(self):
        self.left_widget = QtWidgets.QFrame()
        self.left_widget.setObjectName("left_widget")
        self.left_widget.setMinimumWidth(100)
        self.left_widget.setMaximumWidth(250)
        self.main_layout.addWidget(self.left_widget)
        widget = self.left_widget
        
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
        self.channel_list.itemSelectionChanged.connect(self._action_select_channel)
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
        self.name_text_box.setMaxLength(64)
        self.name_text_box.textEdited.connect(self._action_name_edited)
        you_frame_layout.addWidget(self.name_text_box)

    def _init_make_cframe(self):
        middle_frame = QtWidgets.QFrame()
        middle_frame.setObjectName("middle_frame")
        self.main_layout.addWidget(middle_frame)
        
        middle_frame_layout = QtWidgets.QVBoxLayout()
        middle_frame.setLayout(middle_frame_layout)

        self.center_stacker = QtWidgets.QStackedWidget()
        middle_frame_layout.addWidget(self.center_stacker, stretch=1)

        self.message_box = QtWidgets.QTextEdit()
        self.message_box.setMaximumHeight(100)
        self.message_box.setPlaceholderText("Message")
        self.message_box.setAcceptRichText(False)
        self.message_box.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.message_box.setEnabled(False)
        # self.message_box.textChanged.connect(self._message_box_changed)
        middle_frame_layout.addWidget(self.message_box)

    def add_channel(self, channel_id: int, channel_name: str):
        if channel_id in self.channels:
            raise ValueError("attempted to add channel with same id as existing")
        
        max_index = -1
        for chan in self.channels.values():
            max_index = max(max_index, chan[0])
        
        channel_widget = QtWidgets.QWidget()
        channel_layout = QtWidgets.QVBoxLayout()
        channel_widget.setLayout(channel_layout)

        messages_scrollarea = QtWidgets.QScrollArea(channel_widget)
        messages_layout = QtWidgets.QVBoxLayout()
        messages_widget = QtWidgets.QWidget()
        messages_scrollarea.setWidget(messages_widget)
        messages_widget.setLayout(messages_layout)
        messages_scrollarea.setWidgetResizable(True)
        channel_layout.addWidget(messages_scrollarea)


        channel_list_item = QtWidgets.QListWidgetItem(channel_name)
        channel_list_item.setData(1, channel_id)
        self.channel_list.addItem(channel_list_item)

        self.center_stacker.addWidget(channel_widget)
        self.channels[channel_id] = [max_index + 1, channel_name, [messages_widget, messages_scrollarea, messages_layout], channel_list_item]

    def select_channel(self, channel_id: int):
        if not channel_id in self.channels:
            raise ValueError("Attempted to select a nonexistent channel")
        
        channel = self.channels[channel_id]
        self.center_stacker.setCurrentIndex(channel[0])
        self.channel_list.setCurrentItem(channel[3])

    def add_message(self, channel_id: int, name: str, content: str):
        if not channel_id in self.channels:
            raise ValueError("Attempted to add message to nonexistent channel")
        
        channel = self.channels[channel_id]
        messages_area = channel[2][1]
        messages_layout = channel[2][2]

        msg = GUI_Message(name, content)
        msg.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        msg.adjustSize()

        scrollbar = messages_area.verticalScrollBar()
        on_bottom = scrollbar.sliderPosition() == scrollbar.maximum()
        messages_layout.addWidget(msg, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)
        if on_bottom:
            QtCore.QTimer.singleShot(10, lambda:
                scrollbar.setSliderPosition(scrollbar.maximum()+1)
            )

    def _log(self, lvl: str, msg: str, *fmt):
        self.add_message(-1, lvl, msg % fmt)
        print(f"[{lvl}] {msg % fmt}")
    def log_info(self, msg: str, *fmt):
        self._log("INFO", msg, *fmt)
    def log_warning(self, msg: str, *fmt):
        self._log("WARN", msg, *fmt)
    def log_error(self, msg: str, *fmt):
        self._log("ERROR", msg, *fmt)

    def _update_state(self):
        if self.state == STATE_CONNECTED:
            self.server_menu.actions()[0].setEnabled(False)  # Server/Connect
            self.server_menu.actions()[1].setEnabled(True) # Server/Disconnect
            self.name_text_box.setEnabled(False)
        if self.state == STATE_DISCONNECTED:
            self.server_menu.actions()[0].setEnabled(True)  # Server/Connect
            self.server_menu.actions()[1].setEnabled(False) # Server/Disconnect
            self.name_text_box.setEnabled(True)

    @QtCore.Slot()
    def _menubar_action_about(self):
        print("about")
    @QtCore.Slot()
    def _menubar_action_settings(self):
        print("settings")
    @QtCore.Slot()
    def _menubar_action_connect(self):
        if not self.client.has_username():
            self.log_error("Please set your username first.")
            return
        self.log_info("Connection dialog opened")
        inp, ok = QtWidgets.QInputDialog.getText(self, "Scalar", "Connect to:", QtWidgets.QLineEdit.EchoMode.Normal)
        if not ok:
            self.log_info("Connection dialog aborted")
            return
        if not inp.startswith("scalar://"):
            self.log_error("Connection error: validation failed: invalid scheme (expected 'scalar://')")
            return
        inp = inp[9:]
        if inp.count(':') > 1:
            self.log_error("Connection error: validation failed: invalid uri (can't make out host and port!)")
            return
        host, port = '', 1440
        if inp.count(':') == 0:
            host = inp
        else:
            host, port = inp.split(':')
            try: port = int(port)
            except ValueError:
                self.log_error(f"Connection error: parsing failed: port expected to be an integer, got string ('{port}')")
                return
            if port < 0:
                self.log_error(f"Connection error: validation failed: port not in range ({port} < 0)")
                return
            if port > 65535:
                self.log_error(f"Connection error: validation failed: port not in range ({port} > 65535)")
                return
        if host == '':
            self.log_error("Connection error: validation failed: host expected to be a string, got nothing")
            return
        
        self.log_info(f"Connecting to scalar://{host}:{port}")
        self.state = STATE_CONNECTED
        self._update_state()
        self.client.start_thread(host, port)
            
    @QtCore.Slot()
    def _menubar_action_disconnect(self):
        self.client.end_thread()
        self.state = STATE_DISCONNECTED
        self._update_state()
        self.log_info(f"Disconnected")
    
    @QtCore.Slot()
    def _action_select_channel(self):
        self.select_channel(self.channel_list.currentItem().data(1))

    @QtCore.Slot()
    def _action_name_edited(self):
        self.client.set_username(self.name_text_box.text())

    def closeEvent(self, event):
        if self.client.connected():
            reply = QtWidgets.QMessageBox.question(self, 'Message',
                                     "Are you sure to quit?", QtWidgets.QMessageBox.Yes |
                                     QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.Yes:
                self.client.end_thread()
                event.accept()
            else:
                event.ignore()

    client: scalar0.Scalar0Client = None

    def _init_create_client(self):
        self.client = scalar0.Scalar0Client()
        @self.client.event("on_kicked")
        def _cevent_on_kicked(client: scalar0.Scalar0Client, reason: str):
            self.state = STATE_DISCONNECTED
            self._update_state()
            self.log_warning(f"Kicked: {reason}")

        @self.client.event("on_socket_broken")
        def _cevent_on_socket_broken(client: scalar0.Scalar0Client):
            self.state = STATE_DISCONNECTED
            self._update_state()
            self.log_warning(f"Disconnected: Socket broken for unknown reason")
        self._client_process_events() # start timer
    def _client_process_events(self):
        self.client._threaded_process_events()
        QtCore.QTimer.singleShot(100, self._client_process_events)