from PyQt5 import QtCore, QtGui, QtWidgets
import sys

from ui_resourses import dialog_windows, message_widget


class Ui_MainWindow(QtWidgets.QMainWindow):
    def __init__(self, main_window):
        QtWidgets.QMainWindow.__init__(self)
        self.init_view(main_window)
        self.add_actions()
        self.set_messages_enabled(False)

        self.name = ""
        self.ring_token = ""
        self.is_init_ring_closed = False
        self.init_ring()

        self.message_counter = 0
        self.chat_counter = 0
        self.current_chat = []
        self.chats = dict()
        self.tokens = dict()
        self.previous_chat = ""
        self.default_widget = QtWidgets.QWidget(self.centralwidget)
        self.default_widget.setEnabled(False)
        self.default_widget.setMaximumSize(0, 0)

        self.loading_window = dialog_windows.LoadingWindow(self)

    def init_view(self, main_window):
        f = open('ui_resourses/res/super.stylesheet', 'r')
        self.styleData = f.read()
        f.close()

        main_window.setObjectName("MainWindow")
        main_window.resize(800, 600)
        main_window.setStyleSheet(self.styleData)
        self.setStyleSheet(self.styleData)
        self.centralwidget = QtWidgets.QWidget(main_window)
        self.centralwidget.setStyleSheet("")
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.current_chat_widget = QtWidgets.QWidget(self.centralwidget)
        self.current_chat_widget.setObjectName("current_chat_widget")
        self.gridLayout = QtWidgets.QGridLayout(self.current_chat_widget)
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")

        self.edit_area = QtWidgets.QWidget(self.current_chat_widget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                            QtWidgets.QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.edit_area.sizePolicy().hasHeightForWidth())
        self.edit_area.setSizePolicy(size_policy)
        self.edit_area.setMinimumSize(QtCore.QSize(0, 50))
        self.edit_area.setMaximumSize(QtCore.QSize(16777215, 100))
        self.edit_area.setObjectName("edit_area")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.edit_area)
        self.horizontalLayout_2.setContentsMargins(5, 5, 5, 5)
        self.horizontalLayout_2.setSpacing(10)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.send_message_field = QtWidgets.QPlainTextEdit(self.edit_area)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                            QtWidgets.QSizePolicy.Preferred)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.send_message_field.sizePolicy().hasHeightForWidth())
        self.send_message_field.setSizePolicy(size_policy)
        self.send_message_field.setMinimumSize(QtCore.QSize(477, 40))
        self.send_message_field.setMaximumSize(QtCore.QSize(16777215, 90))
        self.send_message_field.setSizeIncrement(QtCore.QSize(0, 0))
        self.send_message_field.setBaseSize(QtCore.QSize(0, 0))
        self.send_message_field.setStyleSheet("")
        self.send_message_field.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.send_message_field.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        self.send_message_field.setCenterOnScroll(False)
        self.send_message_field.setObjectName("send_message_field")
        self.horizontalLayout_2.addWidget(self.send_message_field)
        self.message_buttons = QtWidgets.QWidget(self.edit_area)
        self.message_buttons.setMaximumSize(QtCore.QSize(40, 16777215))
        self.message_buttons.setObjectName("message_buttons")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.message_buttons)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName("verticalLayout")
        self.send_button = QtWidgets.QPushButton(self.message_buttons)
        self.send_button.setMinimumSize(QtCore.QSize(40, 40))
        self.send_button.setMaximumSize(QtCore.QSize(40, 40))
        self.send_button.setObjectName("send_button")
        self.verticalLayout.addWidget(self.send_button)
        self.attach_button = QtWidgets.QPushButton(self.message_buttons)
        self.attach_button.setMinimumSize(QtCore.QSize(40, 40))
        self.attach_button.setMaximumSize(QtCore.QSize(40, 40))
        self.attach_button.setObjectName("attach_button")
        self.verticalLayout.addWidget(self.attach_button)
        self.horizontalLayout_2.addWidget(self.message_buttons)
        self.gridLayout.addWidget(self.edit_area, 5, 0, 1, 1)
        self.chat_area = QtWidgets.QWidget(self.current_chat_widget)
        self.chat_area.setObjectName("chat_area")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.chat_area)
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.messages_area = QtWidgets.QScrollArea(self.chat_area)
        self.messages_area.setFrameShape(QtWidgets.QFrame.Box)
        self.messages_area.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.messages_area.setLineWidth(1)
        self.messages_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.messages_area.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.messages_area.setWidgetResizable(True)
        self.messages_area.setAlignment(QtCore.Qt.AlignBottom |
                                        QtCore.Qt.AlignJustify)
        self.messages_area.setObjectName("messages_area")
        self.messages_area_layout_w = QtWidgets.QWidget()
        self.messages_area_layout_w.setGeometry(QtCore.QRect(0, 0, 546, 418))
        self.messages_area_layout_w.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.messages_area_layout_w.setObjectName("messages_area_layout")
        self.messages_area_layout = QtWidgets.QFormLayout(self.messages_area_layout_w)
        self.messages_area_layout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.messages_area_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.messages_area_layout.setRowWrapPolicy(QtWidgets.QFormLayout.DontWrapRows)
        self.messages_area_layout.setLabelAlignment(QtCore.Qt.AlignBottom |
                                                    QtCore.Qt.AlignLeading |
                                                    QtCore.Qt.AlignLeft)
        self.messages_area_layout.setFormAlignment(QtCore.Qt.AlignBottom |
                                                   QtCore.Qt.AlignLeading |
                                                   QtCore.Qt.AlignLeft)
        self.messages_area_layout.setContentsMargins(5, 5, 5, 5)
        self.messages_area_layout.setObjectName("formLayout")
        self.messages_area.setWidget(self.messages_area_layout_w)
        self.gridLayout_4.addWidget(self.messages_area, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.chat_area, 2, 0, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.chat_name_label = QtWidgets.QLabel(self.current_chat_widget)
        self.chat_name_label.setMaximumSize(QtCore.QSize(16777215, 40))
        self.chat_name_label.setAlignment(QtCore.Qt.AlignBottom |
                                          QtCore.Qt.AlignLeading |
                                          QtCore.Qt.AlignLeft)
        self.chat_name_label.setIndent(3)
        self.chat_name_label.setObjectName("chat_name_label")
        self.horizontalLayout.addWidget(self.chat_name_label)
        self.refresh_button = QtWidgets.QPushButton(self.current_chat_widget)
        self.refresh_button.setMinimumSize(QtCore.QSize(40, 40))
        self.refresh_button.setMaximumSize(QtCore.QSize(40, 40))
        self.refresh_button.setIconSize(QtCore.QSize(40, 40))
        self.refresh_button.setIcon(QtGui.QIcon("ui_resourses/res/refresh_upd.png"))
        self.refresh_button.setObjectName("refresh_button")
        self.horizontalLayout.addWidget(self.refresh_button)
        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.gridLayout_2.addWidget(self.current_chat_widget, 0, 1, 1, 1)
        self.chat_list_area = QtWidgets.QWidget(self.centralwidget)
        self.chat_list_area.setObjectName("chat_list_area")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.chat_list_area)
        self.gridLayout_5.setContentsMargins(0, 0, 0, 5)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.chat_list = QtWidgets.QListWidget(self.chat_list_area)
        self.chat_list.setMinimumSize(QtCore.QSize(200, 0))
        self.chat_list.setMaximumSize(QtCore.QSize(300, 16777215))
        self.chat_list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.chat_list.setTabKeyNavigation(True)
        self.chat_list.setProperty("showDropIndicator", False)
        self.chat_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.chat_list.setIconSize(QtCore.QSize(20, 20))
        self.chat_list.setTextElideMode(QtCore.Qt.ElideRight)
        self.chat_list.setObjectName("chat_list")
        self.gridLayout_5.addWidget(self.chat_list, 1, 0, 1, 1)
        self.chat_adding_button = QtWidgets.QPushButton(self.chat_list_area)
        self.chat_adding_button.setStyleSheet("")
        self.chat_adding_button.setObjectName("chat_adding_button")
        self.gridLayout_5.addWidget(self.chat_adding_button, 2, 0, 1, 1)
        self.chat_list_label = QtWidgets.QLabel(self.chat_list_area)
        self.chat_list_label.setObjectName("chat_list_label")
        self.gridLayout_5.addWidget(self.chat_list_label, 0, 0, 1, 1)
        self.gridLayout_2.addWidget(self.chat_list_area, 0, 0, 1, 1)
        self.gridLayout_2.setColumnStretch(0, 1)
        self.gridLayout_2.setColumnStretch(1, 5)
        main_window.setCentralWidget(self.centralwidget)

        self.retranslateUi(main_window)
        QtCore.QMetaObject.connectSlotsByName(main_window)

    def retranslateUi(self, main_window):
        _translate = QtCore.QCoreApplication.translate
        main_window.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.send_message_field.setPlaceholderText(_translate("MainWindow", "Message..."))
        self.send_button.setText(_translate("MainWindow", "Send"))
        self.attach_button.setText(_translate("MainWindow", "File"))
        self.chat_name_label.setText(_translate("MainWindow", "Chat name"))
        self.refresh_button.setText(_translate("MainWindow", ""))
        self.chat_adding_button.setText(_translate("MainWindow", "Add chat"))
        self.chat_list_label.setText(_translate("MainWindow", "Chat list"))

    def init_ring(self):
        child_window = dialog_windows.TokenDialog(self)
        result = child_window.exec()
        if result != QtWidgets.QDialog.DialogCode.Accepted:
            QtWidgets.QMessageBox.warning(self, "Error", "You haven't connected to any ring")
            exit(0)

    def add_actions(self):
        self.chat_adding_button.clicked.connect(self.add_chat)
        self.attach_button.clicked.connect(self.file)
        self.send_button.clicked.connect(self.send_message)
        self.refresh_button.clicked.connect(self.refresh)
        self.messages_area.verticalScrollBar().rangeChanged.connect(self.scroll_to_end)
        self.chat_list.itemClicked.connect(self.chat_changed)

    def add_chat(self):
        child_window = dialog_windows.ChatAddingDialog(self)
        result = child_window.exec()
        if result != QtWidgets.QDialog.DialogCode.Accepted:
            QtWidgets.QMessageBox.warning(self, "Error", "You haven't connected to any chat")

    def file(self):
        file = QtWidgets.QFileDialog(self.centralwidget).getOpenFileName()
        print(file[0]) # filename
        # TO DO: add behavior to adding files

    def message(self, name, text, time, img="ui_resourses/res/avatar.jpg"):
        message = message_widget.MessageWidget()
        message.set_name(name)
        message.set_text(text)
        message.set_time(time)
        message.set_image(img)
        self.current_chat += [message]
        self.messages_area_layout.setWidget(self.message_counter,
                                            QtWidgets.QFormLayout.FieldRole, message)
        self.message_counter += 1
        self.send_message_field.setPlainText("")
        self.send_message_field.setFocus()

    def send_message(self):
        text = self.send_message_field.toPlainText()
        if text == "":
            return
        self.message(self.name, text, "10:00")

    def receive_message(self, sender, message, time):
        # TO DO: connect behavior for receiving message
        return

    def scroll_to_end(self, _min: int, _max: int):
        position = self.messages_area.verticalScrollBar().sliderPosition()
        self.messages_area.verticalScrollBar().setSliderPosition(position + 10000000)

    def refresh(self):
        # TO DO: connect behavior to refresh button
        return

    def chat_changed(self):
        item = self.chat_list.currentItem()
        if item is None:
            self.set_messages_enabled(False)
            return

        self.set_messages_enabled(True)

        if self.previous_chat != "":
            if self.previous_chat == item.text():
                return
            self.chats[self.previous_chat] = self.current_chat.copy()
            self.clear_chat()
            self.message_counter = 0
            self.current_chat = self.chats.get(item.text())
            for message in self.current_chat:
                self.messages_area_layout.setWidget(self.message_counter,
                                                    QtWidgets.QFormLayout.FieldRole, message)
                self.message_counter += 1
        self.previous_chat = item.text()

    def clear_chat(self):
        for message in self.current_chat:
            message.setParent(self.default_widget)

    def set_messages_enabled(self, is_enabled: bool):
        self.send_button.setEnabled(is_enabled)
        self.attach_button.setEnabled(is_enabled)
        self.send_message_field.setEnabled(is_enabled)

    def start_loading_window(self):
        self.loading_window.exec()

    def close_loading_window(self):
        self.t.stop()
        self.loading_window.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
