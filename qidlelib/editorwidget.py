import os
from PyQt4.QtCore import QObject, QDir, Qt, pyqtSlot
from PyQt4.QtGui import QPlainTextEdit, QFileDialog, QCompleter, QStringListModel, QTextCursor, QFont


import logging
from insulate.debug import msg
logger = logging.getLogger(__name__)

from syntax import PythonHighlighter
from util import substr, last_unmatched_char



try:
    from PyKDE4.kdecore import *
    from PyKDE4.kdeui import *
    from PyKDE4.kparts import *
    from PyKDE4.ktexteditor import *
    have_kate_part = True
    kate = KTextEditor.EditorChooser.editor()
except:
    have_kate_part = False

try:
    import jedi
    have_jedi = True
except:
    have_jedi = False

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
    INDENT_SIZE = 4
    WORD_STOP_CHARS = " ~!@#$%^&*()+{}|:\"<>?,/;'[]\\-=\n"

    def __init__(self, parent=None):
        super(PlainTextEditorWidget, self).__init__(parent=parent)
        self._widget = QPlainTextEdit(parent)
        self.hilighter = PythonHighlighter(self._widget.document())
        self.name_changed = signal()
        self.local_path = None

        self.font_size = 10
        self.font = QFont("Ubuntu Mono", self.font_size)
        self.widget.setFont(self.font)


        #self._widgetFocusInEvent = self.widget.focusInEvent
        #self.widget.focusInEvent = self.focusInEvent

        self._init_codecompletion()
        self._init_keypresshandling()

    def _init_keypresshandling(self):
        self._widgetKeyPressEvent = self.widget.keyPressEvent
        self.widget.keyPressEvent = self.keyPressEvent
        self.keypress_event_key_hooks = {}
        self.keypress_event_post_hooks = []
        self.keypress_event_pre_hooks = []
        self._register_keypress_hook(self._process_completion_widget,pre=True)
        self._register_keypress_hook(self._process_enter,keys=[Qt.Key_Return])
        self._register_keypress_hook(self._process_backspace,keys=[Qt.Key_Backspace])
        self._register_keypress_hook(self._completion_hook,post=True)

    def _init_codecompletion(self):
        self.completer = QCompleter(
            [kw for kw in PythonHighlighter.keywords if len(kw) > 3])
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.activated.connect(self._insertCompletion)
        self.completer.popup().setStyleSheet(
            "QWidget {border-width: 1px; border-color: black;}")
        self.completer.popup().setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff)
        self.completer.setWidget(self.widget)
        if have_jedi:
            self.completion_enabled = True
        else:
            self.completion_enabled = False


    def _register_keypress_hook(self, hook, keys=None, pre=False, post=False):
        """ Registers hooks into the keypress event handling mechanism.

             @hook ... a function taking one argument --- the event

             If @key is not None then it is a list of keys for which the hook will be activated.
             If @pre is True, then the hook will be called before key specific hooks.
             If @post is True, then the hook will be called after key specific hooks.

             Processing events will stop once one of the hooks returns True.
        """
        if keys is not None:
            for k in keys:
                if k not in self.keypress_event_key_hooks:
                    self.keypress_event_key_hooks[k] = []
                    self.keypress_event_key_hooks[k].append(hook)
        if pre:
            self.keypress_event_pre_hooks.append(hook)
        if post:
            self.keypress_event_pre_hooks.append(hook)




    def open_file(self, fname=None):
        if fname is None:
            fname = QFileDialog.getOpenFileName(
                self.widget, "Open File", QDir.currentPath(), "Python Source Files (*.py)")
        try:
            self.content = open(fname,'r').read()
            self.name_changed.emit(self.name)
        except Exception, e:
            logger.warn("Unable read file "+fname+" (exception:"+e+" occured)")

    @property
    def name(self):
        if self.local_path:
            return os.path.basename(self.local_path)
        else:
            return ""

    @property
    def path(self):
        return self.local_path or ""

    def file_dir(self):
        if self.local_path is not None:
            return os.path.dirname(self.local_path)
        else:
            return None

    @property
    def content(self):
        return unicode(self.widget.document().toPlainText())

    @content.setter
    def content(self,cont):
        self.widget.document().setPlainText(cont)

    @property
    def widget(self):
        return self._widget

    @property
    def _currentCursor(self):
        return self._widget.textCursor()

    @_currentCursor.setter
    def _currentCursor(self,cursor):
        self.widget.setTextCursor(cursor)

    @property
    def _cursorPos(self):
        return self._currentCursor.position()

    @property
    def _linecol(self):
        """ Returns the pair (line, col) determining
            the position of the cursor. lines start from 1,
            columns start from 0 """
        content = self.content[:self._cursorPos]
        line = 1
        col = 0
        for char in content:
            if char == '\n':
                line += 1
                col = 0
            else:
                col += 1
        return (line, col)

    def _wordUnderCursor(self,center_char=""):
        """ Returns the word which would be under the cursor after the
            insertion of center_char at the cursor position. """
        if center_char in PlainTextEditorWidget.WORD_STOP_CHARS:
            return ""

        cpos = self._cursorPos
        content = self.content


        prev = substr(content,cpos-1,PlainTextEditorWidget.WORD_STOP_CHARS,direction = -1)
        post = substr(content,cpos,PlainTextEditorWidget.WORD_STOP_CHARS,direction = 1)
        return prev + center_char + post

    def _line(self, line_no = None):
        """ Returns the content of the current line. """
        if line_no is None:
            line_no, col = self._linecol
        return self.content.split('\n')[line_no-1]

    def _indentLevel(self, line_no=None, spaces=True):
        """ Returns the indent level of line number @line_no.
            The default value of @line_no is None which means
            the current line. If @spaces is True, the indent
            level will be converted the number of spaces, otherwise
            it will be the number of full 'Indents'
        """
        ln = self._line(line_no)
        pos = 0
        while pos < len(ln):
            if not ln[pos] in " \t":
                if spaces:
                    return pos
                else:
                    return pos/PlainTextEditorWidget.INDENT_SIZE
            pos += 1
        if spaces:
            return pos
        else:
            return pos/PlainTextEditorWidget.INDENT_SIZE


    def _unmatched_position(self):
        """ Returns the position of the nearest unmatched
            element (i.e. (, {, [, ', " ) to the left
            of the current cursor (but on the same line)
            or None if there is no unmatched element left
            of the cursor on the current line.
        """
        ln = self._line()
        lnum, col = self._linecol
        matching_chars = [ ('"','"'),
                           ('(',')'), ('{','}'), ('[',']') ]
        return last_unmatched_char( ln, matching_chars )


    @pyqtSlot(unicode)
    def _insertCompletion(self, completion):
        insertion = completion[len(self.completer.completionPrefix()):]
        if len(insertion) == 0:
            self._process_enter()
        else:
            c = self._currentCursor
            c.movePosition(QTextCursor.Left)
            c.movePosition(QTextCursor.EndOfWord)
            c.insertText(insertion)
            self._currentCursor = c

    def _process_enter(self,event=None):
        prepend_spaces = 0
        pos =  self._unmatched_position()
        if pos is not None:
            prepend_spaces = pos+1
        else:
            if self._line().strip().endswith(':'):
                logger.debug("New Function:")
                logger.debug(msg("Full indents:", self._indentLevel(spaces=False)))
                prepend_spaces = (self._indentLevel(spaces=False)+1)*PlainTextEditorWidget.INDENT_SIZE
            else:
                prepend_spaces = self._indentLevel()
        self._currentCursor.insertText('\n'+' '*prepend_spaces)
        return True

    def _process_backspace(self,event=None):
        cur_line = self._line()
        l,col = self._linecol
        c = self._currentCursor
        if len(cur_line[:col].strip('\n \t')) == 0:
            lvl = self._indentLevel()
            delchars = lvl % PlainTextEditorWidget.INDENT_SIZE
            if delchars == 0 and lvl >0:
                delchars = PlainTextEditorWidget.INDENT_SIZE
            else:
                delchars = 1
        else:
            delchars = 1
        for i in range(delchars):
            c.deletePreviousChar()
        return True



    def _process_completion_widget(self, event):
        if self.completer.popup().isVisible():
            if event.key() in [Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Up, Qt.Key_Down]:
                event.ignore()
                return True
            elif event.key() in [Qt.Key_Home]:
                self.completer.popup().hide()
        return False

    def _completion_hook(self, event):
        if not (self.completion_enabled and len(event.text()) != 0):
            return False
        completion_prefix = self._wordUnderCursor(center_char=unicode(event.text()))
        #logger.debug("cpt:"+completion_prefix)
        if len(completion_prefix) > 2:
            #logger.debug("cp:"+completion_prefix)
            line,col = self._linecol
            jedi_compl = jedi.Script(self.content,
                                        line,
                                        col,
                                        source_path = self.file_dir())
            try:
                completions = jedi_compl.complete()
                model = QStringListModel([c.word for c in completions])
                self.completer.setModel(model)
                self.completer.setCompletionPrefix(unicode(completion_prefix).strip(' '))
                self.completer.popup().setCurrentIndex(
                        self.completer.completionModel().index(0, 0))

                cursor_rect = self.widget.cursorRect()
                cursor_rect.setWidth(self.completer.popup().sizeHintForColumn(0)
                                        + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(cursor_rect)
            except:
                self.completer.popup().hide()
                self.widget.clearFocus()
                self.widget.setFocus(Qt.ActiveWindowFocusReason)
        else:
                self.completer.popup().hide()
                self.widget.clearFocus()
                self.widget.setFocus(Qt.ActiveWindowFocusReason)
        return False

    def focusInEvent(self, event):
        self.completer.setWidget(self.widget)
        self._widgetFocusInEvent(event)

    def keyPressEvent(self, event):
        for h in self.keypress_event_pre_hooks:
            if h(event):
                return
        if event.key() in self.keypress_event_key_hooks:
            for h in self.keypress_event_key_hooks[event.key()]:
                if h(event):
                    return
        for h in self.keypress_event_post_hooks:
            if h(event):
                return
        return self._widgetKeyPressEvent(event)
