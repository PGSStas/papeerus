import PyQt5
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QDialog


class TokenDialog(QtWidgets.QDialog):
    def __init__(self, parent_window):
        super(TokenDialog, self).__init__(parent_window)
        self.parent = parent_window

        self.setStyleSheet(self.parent.styleData)

        self.setWindowTitle("Ring connection")
        self.setFixedSize(800, 200)
        self.v_layout = QtWidgets.QVBoxLayout(self)
        self.name_label = QtWidgets.QLabel("Enter your name:")
        self.v_layout.addWidget(self.name_label)
        self.name_edit = QtWidgets.QPlainTextEdit()
        self.name_edit.setFixedSize(782, 30)
        self.v_layout.addWidget(self.name_edit)
        self.token_label = QtWidgets.QLabel("Enter the ring token or push \"Create\" button "
                                            "to create new ring:")
        self.v_layout.addWidget(self.token_label)
        self.token_edit = QtWidgets.QPlainTextEdit()
        self.token_edit.setFixedSize(782, 30)
        self.v_layout.addWidget(self.token_edit)
        self.button_widget = QtWidgets.QWidget(self)
        self.h_layout = QtWidgets.QHBoxLayout(self.button_widget)
        self.accept_button = QtWidgets.QPushButton("Accept")
        self.create_button = QtWidgets.QPushButton("Create")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.h_layout.addWidget(self.accept_button)
        self.h_layout.addWidget(self.create_button)
        self.h_layout.addWidget(self.cancel_button)
        self.v_layout.addWidget(self.button_widget)

        self.name = ""
        self.token = ""
        self.ring_is_created = False
        self.add_actions()

    def add_actions(self):
        self.accept_button.clicked.connect(self.accept_ring)
        self.create_button.clicked.connect(self.create_ring)
        self.cancel_button.clicked.connect(self.cancel)

    def accept_ring(self):
        if self.name_edit.toPlainText() == "" or self.token_edit.toPlainText() == "":
            QtWidgets.QMessageBox.warning(self, "Error", "You should fill the fields")
            return
        self.name = self.name_edit.toPlainText()
        self.token = self.token_edit.toPlainText()
        status, _ = self.parent.client.register_network(self.token, self.name)
        if not status:
            QtWidgets.QMessageBox.warning(self, "Error", "Nickname was taken")
            return
        self.parent.name = self.name
        self.parent.token = self.token
        self.done(QDialog.Accepted)

    def create_ring(self):
        if not self.ring_is_created:
            self.name = self.name_edit.toPlainText()
            self.token = self.parent.client.create_network(self.name)
            self.token_label.setText("New ring was created. It's token:")
            self.token_edit.setReadOnly(True)
            self.token_edit.setPlainText(self.token)
            self.create_button.setText("Done")
            self.accept_button.setEnabled(False)
            self.ring_is_created = True
        else:
            if self.name_edit.toPlainText() == "":
                QtWidgets.QMessageBox.warning(self, "Error", "You should fill the name field")
                return

            self.parent.name = self.name
            self.parent.token = self.token
            self.done(QDialog.Accepted)

    def cancel(self):
        self.reject()


class ChatAddingDialog(QtWidgets.QDialog):
    def __init__(self, parent_window):
        super(ChatAddingDialog, self).__init__(parent_window)
        self.parent = parent_window

        self.setStyleSheet(self.parent.styleData)

        self.setWindowTitle("Chat adding")
        self.setFixedSize(600, 200)
        self.v_layout = QtWidgets.QVBoxLayout(self)
        self.name_label = QtWidgets.QLabel("Enter chat name:")
        self.v_layout.addWidget(self.name_label)
        self.name_edit = QtWidgets.QPlainTextEdit()
        self.name_edit.setFixedSize(582, 30)
        self.v_layout.addWidget(self.name_edit)
        self.token_label = QtWidgets.QLabel("Enter the chat token or push \"Create\" button "
                                            "to create new chat:")
        self.v_layout.addWidget(self.token_label)
        self.token_edit = QtWidgets.QPlainTextEdit()
        self.token_edit.setFixedSize(582, 30)
        self.v_layout.addWidget(self.token_edit)
        self.button_widget = QtWidgets.QWidget(self)
        self.h_layout = QtWidgets.QHBoxLayout(self.button_widget)
        self.accept_button = QtWidgets.QPushButton("Accept")
        self.create_button = QtWidgets.QPushButton("Create")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.h_layout.addWidget(self.accept_button)
        self.h_layout.addWidget(self.create_button)
        self.h_layout.addWidget(self.cancel_button)
        self.v_layout.addWidget(self.button_widget)

        self.chat_name = ""
        self.chat_token = ""
        self.ring_is_created = False
        self.add_actions()

    def add_actions(self):
        self.accept_button.clicked.connect(self.accept_chat)
        self.create_button.clicked.connect(self.create_chat)
        self.cancel_button.clicked.connect(self.cancel)

    def accept_chat(self):
        if self.name_edit.toPlainText() == "" or self.token_edit.toPlainText() == "":
            QtWidgets.QMessageBox.warning(self, "Error", "You should fill the fields")
            return

        self.chat_name = self.name_edit.toPlainText()
        self.chat_token = self.token_edit.toPlainText()
        # TO DO: connect behavior for connecting the existing chat
        self.parent.chat_list.addItem(self.chat_name)
        self.parent.chats[self.chat_name] = []
        self.parent.tokens[self.chat_name] = self.chat_token
        self.done(QDialog.Accepted)

    def create_chat(self):
        if not self.ring_is_created:
            self.chat_name = self.name_edit.toPlainText()
            # TO DO: connect behavior for creating a new chat
            # token = ...
            self.chat_token = "default"
            self.token_label.setText("New chat was created. It's token:")
            self.token_edit.setPlainText(self.chat_token)
            self.create_button.setText("Done")
            self.accept_button.setEnabled(False)
            self.ring_is_created = True

        else:
            if self.name_edit.toPlainText() == "":
                QtWidgets.QMessageBox.warning(self, "Error", "You should fill the name field")
                return

            self.parent.chat_list.addItem(self.chat_name)
            self.parent.chats[self.chat_name] = []
            self.parent.tokens[self.chat_name] = self.chat_token
            self.done(QDialog.Accepted)

    def cancel(self):
        self.reject()


class LoadingWindow(QtWidgets.QDialog):
    def __init__(self, parent_window):
        super(LoadingWindow, self).__init__(parent_window)
        self.parent = parent_window

        self.setStyleSheet(self.parent.styleData)

        self.setWindowTitle("Loading...")
        self.setFixedSize(200, 50)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        self.v_layout = QtWidgets.QVBoxLayout(self)
        self.name_label = QtWidgets.QLabel("Loading...")
        self.name_label.setAlignment(QtCore.Qt.AlignHCenter)
        self.v_layout.addWidget(self.name_label)

    def close(self):
        self.accept()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        event.ignore()
