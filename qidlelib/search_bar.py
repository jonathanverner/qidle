from PyQt4.QtCore import QObject, QDir, Qt, pyqtSlot, pyqtSignal
from PyQt4.QtGui import QPlainTextEdit, QFileDialog, QCompleter, QStringListModel, QTextCursor, QFont, QKeySequence, QMessageBox
from PyQt4.QtGui import QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QWidget, QFrame, QAction

class search_bar(QWidget):
    """ A simple search bar widget """
    search_term_changed=pyqtSignal(unicode)
    search_canceled=pyqtSignal()
    next_match=pyqtSignal()
    prev_match=pyqtSignal()

    def __init__(self, parent):
        super(search_bar, self).__init__(parent=parent)

        self._search_layout = QHBoxLayout()
        self._find_label = QLabel(self.tr("Find: "))
        self._found_matches_label = QLabel()
        self._find_input = QLineEdit()
        self._next_button = QPushButton(self.tr("&Next"))
        self._prev_button = QPushButton(self.tr("&Prev"))
        self._search_layout.addWidget(self._find_label)
        self._search_layout.addWidget(self._find_input)
        self._search_layout.addWidget(self._next_button)
        self._search_layout.addWidget(self._prev_button)
        self._search_layout.addWidget(self._found_matches_label)
        self.setLayout(self._search_layout)

        self.cancel_action = QAction(self)
        self.next_action = QAction(self)
        self.prev_action = QAction(self)

        self.addAction(self.cancel_action)
        self.cancel_action.setShortcut(QKeySequence(self.tr("Esc")))
        self.cancel_action.triggered.connect(self.search_canceled)

        self.addAction(self.next_action)
        self.next_action.setShortcut(Qt.Key_Return)
        self.next_action.triggered.connect(self.next_match)
        self._next_button.clicked.connect(self.next_action.trigger)

        self.addAction(self.prev_action)
        #self.prev_action.setShortcut(QKeySequence(self.tr("Alt+P")))
        self.prev_action.triggered.connect(self.prev_match)
        self._prev_button.clicked.connect(self.prev_action.trigger)

        self._find_input.textChanged.connect(self.search_term_changed)

    def setFocus(self):
        """ Gives the line edit input focus """
        self._find_input.setFocus()
        txt = self._find_input.text()
        if len(txt) > 0:
            self.search_term_changed.emit(txt)

    def found_matches(self, count):
        """ Updates the information text with the number of matches found
            and colors the background of the line edit red / green
            if no matches/some matches were found
        """
        if count == 0:
            self.setStyleSheet(""" QLineEdit { background-color: #FF7F6E; } """)
            self._found_matches_label.setText(self.tr("Not found"))
        else:
            self.setStyleSheet(""" QLineEdit { background-color: #98FF94; } """)
            self._found_matches_label.setText(self.tr(str(count)+" matches found"))


