from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QPixmap
import os
import platform
import subprocess


class ClickableLabel(QtWidgets.QLabel):
    def __init__(self, parent, file: str):
        super(ClickableLabel, self).__init__(parent)
        self.file = file

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self.open_file(self.file)

    def enterEvent(self, event: QtCore.QEvent) -> None:
        super(ClickableLabel, self).enterEvent(event)
        self.setStyleSheet("QLabel{ text-decoration: underline; }")

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        super(ClickableLabel, self).leaveEvent(event)
        self.setStyleSheet("QLabel{  }")

    def open_file(self, path: str):
        if platform.system() == "Windows":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])


class MessageWidget(QtWidgets.QWidget):
    def __init__(self, clickable=False, file=""):
        super().__init__()
        self.setObjectName("message_widget")
        self.resize(600, 60)
        self.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.gridLayout = QtWidgets.QGridLayout(self)
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName("gridLayout")
        if not clickable:
            self.message_text_label = QtWidgets.QLabel(self)
        else:
            self.message_text_label = ClickableLabel(self, file)
        self.message_text_label.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.message_text_label.setFrameShadow(QtWidgets.QFrame.Plain)
        self.message_text_label.setIndent(5)
        self.message_text_label.setMargin(5)
        self.message_text_label.setObjectName("message_text_label")
        self.time_label = QtWidgets.QLabel(self)
        self.time_label.setMaximumSize(QtCore.QSize(175, 40))
        self.time_label.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.time_label.setObjectName("time_label")
        self.sender_name_label = QtWidgets.QLabel(self)
        self.sender_name_label.setMinimumSize(QtCore.QSize(0, 0))
        self.sender_name_label.setMaximumSize(QtCore.QSize(16777215, 20))
        self.sender_name_label.setTextFormat(QtCore.Qt.AutoText)
        self.sender_name_label.setScaledContents(False)
        self.sender_name_label.setIndent(10)
        self.sender_name_label.setObjectName("sender_name_label")
        self.gridLayout.addWidget(self.message_text_label, 1, 1, 1, 1)
        self.image = QtWidgets.QLabel(self)
        self.image.setMinimumSize(QtCore.QSize(40, 40))
        self.image.setMaximumSize(QtCore.QSize(40, 40))
        self.image.setText("")
        self.image.setObjectName("image")
        self.gridLayout.addWidget(self.image, 1, 0, 1, 1, QtCore.Qt.AlignBottom)
        self.gridLayout.addWidget(self.time_label, 1, 2, 1, 1, QtCore.Qt.AlignBottom)
        self.gridLayout.addWidget(self.sender_name_label, 0, 1, 1, 1)

        self.set_name("Name")
        self.set_text("Text")
        self.set_time("00:00")

    def set_name(self, name: str):
        self.sender_name_label.setText(name)

    def set_text(self, text: str):
        self.message_text_label.setText(text)

    def get_text(self):
        return self.message_text_label.text()

    def set_time(self, time: str):
        self.time_label.setText(time)

    def set_image(self, img_file: str):
        self.image.setPixmap(QPixmap(img_file))
