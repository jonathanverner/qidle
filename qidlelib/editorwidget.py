from PyQt4.QtCore import QObject, QDir
from PyQt4.QtGui import QPlainTextEdit, QFileDialog

import logging
from insulate.debug import msg
logger = logging.getLogger(__name__)


try:
    from PyKDE4.kdecore import *
    from PyKDE4.kdeui import *
    from PyKDE4.kparts import *
    from PyKDE4.ktexteditor import *
    have_kate_part = True
    kate = KTextEditor.EditorChooser.editor()
except:
    have_kate_part = False

from insulate.utils import signal


def get_editor_widget(parent=None):
    if have_kate_part:
        return KateEditorWidget(parent)
    else:
        return PlainTextEditorWidget(parent)


def show_config_dialog(parent=None):
    if have_kate_part:
        kate.configDialog(parent)
        kate.writeConfig()
    else:
        return


class KateEditorWidget(QObject):
    def __init__(self, parent=None):
        super(KateEditorWidget, self).__init__(parent=parent)

        self.name_changed = signal()

        self.view = kate.createDocument(self).createView(parent)
        self.doc = self.view.document()
        self.doc.setMode("Python")

        self.widget.setStyleSheet("""
            QFrame { border:none }
            QScrollBar:horizontal {
                width: 0px;
            }
        """)
        self.doc.documentNameChanged.connect(self._name_changed)

    def _name_changed(self, doc):
        logger.debug(self.name)
        self.name_changed.emit(self.name)

    def open_file(self, fname=None):
        if fname is None:
            fname = QFileDialog.getOpenFileName(
                self.widget, "Open File", QDir.currentPath(), "Python Source Files (*.py)")
        self.doc.openUrl(KUrl(fname))

    @property
    def name(self):
        return self.doc.documentName()

    @property
    def path(self):
        return self.doc.localFilePath()

    @property
    def widget(self):
        return self.view

    @property
    def content(self):
        return unicode(self.doc.text())

    @content.setter
    def content(self, value):
        self.doc.setText(value)


class PlainTextEditorWidget(QObject):
    def __init__(self, parent=None):
        self._widget = QPlainTextEdit(parent)

    def open_file(self, fname=None):
        if fname is None:
            fname = QFileDialog.getOpenFileName(
                self.widget, "Open File", QDir.currentPath(), "Python Source Files (*.py)")

    @property
    def name(self):
        return ""

    @property
    def content(self):
        return self.widget.document().toPlainText()

    @property
    def widget(self):
        return self._widget
