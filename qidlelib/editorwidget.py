import os
from PyQt4.QtCore import QObject, QDir, Qt, pyqtSlot
from PyQt4.QtGui import QPlainTextEdit, QFileDialog, QCompleter, QStringListModel, QTextCursor, QFont, QMessageBox
from PyQt4.QtGui import QVBoxLayout, QAction, QKeySequence, QWidget, QTextEdit, QColor


import logging
from insulate.debug import msg
logger = logging.getLogger(__name__)

from syntax import PythonHighlighter
from util import substr, last_unmatched_char
from search_bar import search_bar



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

        self.editor_widget.setStyleSheet("""
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
        return self.doc.openUrl(KUrl(fname))

    def close(self):
        return self.doc.documentSave()

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


class PlainTextEditorWidget(QObject,object):
    INDENT_SIZE = 4
    WORD_STOP_CHARS = " ~!@#$%^&*()+{}|:\"<>?,/;.'[]\\-=\n"

    def __init__(self, parent=None):
        super(PlainTextEditorWidget, self).__init__(parent=parent)
        self._construct_widget(parent)

        self.find_action = QAction(self.editor_widget)
        self.editor_widget.addAction(self.find_action)
        self.find_action.setShortcut(QKeySequence(self.tr("Ctrl+F")))
        self.find_action.triggered.connect(self._show_search_bar)


        self.name_changed = signal()
        self.local_path = None


        #self._widgetFocusInEvent = self.editor_widget.focusInEvent
        #self.editor_widget.focusInEvent = self.focusInEvent

        self._init_codecompletion()
        self._init_keypresshandling()

    def _show_search_bar(self):
        logger.debug("")
        self._search_widget.show()
        self._search_widget.setFocus()

    def _construct_widget(self, parent):
        """ Constructs the widget:
              -- the QPlainTextEdit
              -- the search bar
        """

        self._widget_layout = QVBoxLayout()
        self._widget_layout.setMargin(0)

        # Search Widget
        self._search_widget = search_bar(parent)
        self._search_widget.search_term_changed.connect(self.find)
        self._search_widget.search_canceled.connect(self.cancel_find)
        self._search_widget.next_match.connect(self.next_match)
        self._search_widget.prev_match.connect(self.prev_match)

        # Text Editor Widget
        self._editor_widget = QPlainTextEdit(parent)
        self._widget_layout.addWidget(self.editor_widget)
        self._widget_layout.addWidget(self._search_widget)
        self.hilighter = PythonHighlighter(self.editor_widget.document())
        self.font_size = 10
        self.font = QFont("Ubuntu Mono", self.font_size)
        self.editor_widget.setFont(self.font)
        self.editor_widget.document().modificationChanged.connect(self._emit_name_change)

        self._widget = QWidget(parent)
        self.editor_widget.setStyleSheet("""
            QWidget { border:none; }
            }
        """)
        self._search_widget.hide()
        self.widget.setLayout(self._widget_layout)


    def _init_keypresshandling(self):
        self._widgetKeyPressEvent = self.editor_widget.keyPressEvent
        self.editor_widget.keyPressEvent = self.keyPressEvent
        self.keypress_event_key_hooks = {}
        self.keypress_keysequence_hooks = []
        self.keypress_event_post_hooks = []
        self.keypress_event_pre_hooks = []
        self._register_keypress_hook(self._process_completion_widget,pre=True)
        self._register_keypress_hook(self._process_enter,keys=[Qt.Key_Return])
        self._register_keypress_hook(self._process_backspace,keys=[Qt.Key_Backspace])
        self._register_keypress_hook(self._completion_hook,post=True)
        self._register_keypress_hook(self._process_tab,keys=[Qt.Key_Tab])
        self._register_keypress_hook(self._process_home,keys=[Qt.Key_Home], keysequences=[QKeySequence.MoveToStartOfLine])

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
        self.completer.setWidget(self.editor_widget)
        if have_jedi:
            self.completion_enabled = True
        else:
            self.completion_enabled = False


    def _register_keypress_hook(self, hook, keys=None, pre=False, post=False, keysequences = None):
        """ Registers hooks into the keypress event handling mechanism.

             @hook ... a function taking one argument --- the event

             If @key is not None then it is a list of keys for which the hook will be activated.
             If @keysequence is not None then it is a list of sequences whose match will activate the hook
             If @pre is True, then the hook will be called before key specific hooks.
             If @post is True, then the hook will be called after key specific hooks.

             Processing events will stop once one of the hooks returns True.
        """
        if keys is not None:
            for k in keys:
                if k not in self.keypress_event_key_hooks:
                    self.keypress_event_key_hooks[k] = []
                    self.keypress_event_key_hooks[k].append(hook)
        if keysequences is not None:
            for ks in keysequences:
                self.keypress_keysequence_hooks.append((ks,hook))
        if pre:
            self.keypress_event_pre_hooks.append(hook)
        if post:
            self.keypress_event_pre_hooks.append(hook)


    def find(self,term):
        """ Searches for the term @term and
              -- hilights all of its occurances
              -- moves to the first occurance
              -- informs the search_widget about the number of occurances
              -- saves the cursors of the occurances to the _matches list
        """
        color = QColor(Qt.yellow).lighter(130)
        selections = []
        goto_cursor = self._currentCursor
        self.editor_widget.moveCursor(QTextCursor.Start)
        count = 0
        self._matches = []
        self._match_num = 0
        while self.editor_widget.find(term):
            if count == 0:
                goto_cursor = self._currentCursor
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(color)
            sel.cursor = self._currentCursor
            selections.append(sel)
            self._matches.append(self._currentCursor)
            count += 1
        self.editor_widget.setExtraSelections(selections)
        self._currentCursor = goto_cursor
        self._search_widget.found_matches(count)

    def next_match(self):
        """ Moves the cursor to the next occurance of the term
            we are currently actively searching for.
        """
        if len(self._matches) == 0:
            return
        self._match_num += 1
        if self._match_num >= len(self._matches):
            self._match_num = 0
        self._currentCursor = self._matches[self._match_num]

    def prev_match(self):
        """ Moves the cursor to the previous occurance of the term
            we are currently actively searching for.
        """
        if len(self._matches) == 0:
            return
        self._match_num -= 1
        if self._match_num < 0:
            self._match_num = len(self._matches)-1
        self._currentCursor = self._matches[self._match_num]

    def cancel_find(self):
        """ Clears all hilighted search terms and matches """
        self.editor_widget.setExtraSelections([])
        self._search_widget.hide()
        self._matches = []
        self._match_num = 0

    def save_as(self, fname=None):
        """ Saves the contents of the widget to the file with filename @fname.
            If @fname is none, it asks the user for a filename.

            Returns True if successful, False otherwise
            (i.e. exception occured during writing, we do not yet have a
            filename and the user canceled the file dialog)
        """
        if fname is None:
            fname = QFileDialog.getSaveFileName(
                self.widget, "Save File As", QDir.currentPath(), "Python Source Files (*.py)")
            if len(fname) == 0:
                return False

        try:
            open(fname,'w').write(self.content)
            self.local_path = unicode(fname)
            self.modified = False
            self._emit_name_change()
        except Exception, e:
            logger.error("Unable to write file "+fname+" (exception:"+str(e)+" occured)")
            return False
        return True

    def save(self):
        """ Saves the contents of the widget to the current file.
            If there is no current file, asks the user for a filename
            where to save it.

            Returns True if successful, False otherwise
            (i.e. exception occured during writing, we do not yet have a
            filename and the user canceled the file dialog)
        """
        return self.save_as(self.local_path)

    def open_file(self, fname=None):
        """ Loads the file @fname into the widget. If @fname is None,
            prompts the user for a filename.

            Returns True if successful, False otherwise
            (i.e. exception occured during writing, we do not yet have a
            filename and the user canceled the file dialog)
        """
        if fname is None:
            fname = QFileDialog.getOpenFileName(
                self.widget, "Open File", QDir.currentPath(), "Python Source Files (*.py)")
            if len(fname) == 0:
                return False
        try:
            self.content = open(unicode(fname),'r').read()
            self.local_path = unicode(fname)
            self.modified = False
            self._emit_name_change()
        except Exception, e:
            logger.warn("Unable to read file "+fname+" (exception:"+str(e)+" occured)")
            return False
        return True

    def close(self):
        """ Tries to save changes to the file, if it is modified.
            Returns True if successful False otherwise.
        """
        if not self.modified:
            return True
        else:
            dlg = QMessageBox()
            dlg.setText(dlg.tr("The document \""+self.display_name[2:]+"\" has unsaved changes."))
            dlg.setInformativeText(dlg.tr("Would you like to save them?"))
            dlg.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            dlg.setDefaultButton(QMessageBox.Save)
            dlg.setIcon(QMessageBox.Warning)
            ret = dlg.exec_()
            if ret == QMessageBox.Save:
                return self.save()
            elif ret == QMessageBox.Discard:
                return True
            elif ret == QMessageBox.Cancel:
                return False

    @property
    def modified(self):
        """ True if the document has been modified by the user. """
        return self.editor_widget.document().isModified()

    @modified.setter
    def modified(self, value):
        self.editor_widget.document().setModified(value)

    @property
    def name(self):
        """ Returns the last part of the filepath or "" if no
            file is associated with the document
        """
        if self.local_path:
            return os.path.basename(self.local_path)
        else:
            return ""

    @property
    def display_name(self):
        """ Returns a name of the document suitable for display. """
        nm = self.name
        if len(nm) == 0:
            nm = self.editor_widget.tr("Untitled")
        if self.modified:
            nm = "* "+nm
        return nm

    @pyqtSlot()
    def _emit_name_change(self):
        self.name_changed.emit(self.display_name)

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
        return unicode(self.editor_widget.document().toPlainText())

    @content.setter
    def content(self,cont):
        self.editor_widget.document().setPlainText(cont)

    @property
    def widget(self):
        return self._widget

    @property
    def editor_widget(self):
        """ The underlying QPlainTextEdit """
        return self._editor_widget


    @property
    def _currentCursor(self):
        return self.editor_widget.textCursor()

    @_currentCursor.setter
    def _currentCursor(self,cursor):
        self.editor_widget.setTextCursor(cursor)

    @property
    def _cursorPos(self):
        return self._currentCursor.position()

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

    def _linecol(self, include_line_text = False):
        """ If @include_line_text is False (default) returns the pair (line, col) determining
            the position of the cursor. lines start from 1, columns start from 0.
            If @include_line_text is True, returns the triple (text, line, col), where
            (line,col) is as above and text is the text of the current line excluding the
            newline.
        """
        content = self.content[:self._cursorPos]
        line = 1
        col = 0
        text = ''
        l_start_pos = 0
        pos = 0
        for char in content:
            if char == '\n':
                line += 1
                col = 0
                text = ''
                l_start_pos = pos+1
            else:
                col += 1
            pos += 1
        if include_line_text:
            for char in self.content[self._cursorPos:]:
                pos += 1
                if char == '\n':
                    break
            return (self.content[l_start_pos:pos], line, col)
        else:
            return (line, col)

    def _line(self, line_no = None):
        """ Returns the content of the current line. """
        if line_no is None:
            text, line_no, col = self._linecol(include_line_text=True)
            return text
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
        ln,lnum,col = self._linecol(include_line_text=True)
        matching_chars = [ ('"','"'),
                           ('(',')'), ('{','}'), ('[',']') ]
        return last_unmatched_char( ln, matching_chars )


    def _process_home(self, event=None):
        ln, lnum, col = self._linecol(include_line_text=True)
        pos = 0
        while pos < len(ln) and ln[pos] in ' \t':
            pos += 1
        c = self._currentCursor
        if col == pos:
            return False

        if event.modifiers() & Qt.ShiftModifier:
            move_type = QTextCursor.KeepAnchor
        else:
            move_type = QTextCursor.MoveAnchor

        if col > pos:
            c.movePosition(QTextCursor.Left, move_type, col-pos)
        else:
            c.movePosition(QTextCursor.Right, move_type, pos-col)

        self._currentCursor = c
        return True

    def _process_tab(self, event=None):
        self._currentCursor.insertText(' '*PlainTextEditorWidget.INDENT_SIZE)
        return True

    def _process_enter(self,event=None):
        prepend_spaces = 0
        line_text,l,col = self._linecol(include_line_text = True)
        if col == 0:
            prepend_spaces = 0
        else:
            pos =  self._unmatched_position()
            if pos is not None:
                prepend_spaces = pos+1
            else:
                if line_text.strip().endswith(':'):
                    prepend_spaces = (self._indentLevel(spaces=False)+1)*PlainTextEditorWidget.INDENT_SIZE
                else:
                    prepend_spaces = self._indentLevel()
        self._currentCursor.insertText('\n'+' '*prepend_spaces)
        return True

    def _process_backspace(self,event=None):
        cur_line,l,col = self._linecol(include_line_text=True)
        c = self._currentCursor
        if col > 0 and len(cur_line[:col].strip('\n \t')) == 0:
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
        if len(completion_prefix) > 0 or event.text() == '.':
            line,col = self._linecol()
            src = self.content[:self._cursorPos]+unicode(event.text())+self.content[self._cursorPos:]
            jedi_compl = jedi.Script(src,
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

                cursor_rect = self.editor_widget.cursorRect()
                cursor_rect.setWidth(self.completer.popup().sizeHintForColumn(0)
                                        + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(cursor_rect)
            except:
                self.completer.popup().hide()
                self.editor_widget.clearFocus()
                self.editor_widget.setFocus(Qt.ActiveWindowFocusReason)
        else:
                self.completer.popup().hide()
                self.editor_widget.clearFocus()
                self.editor_widget.setFocus(Qt.ActiveWindowFocusReason)
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

        for (seq, h) in self.keypress_keysequence_hooks:
            if event.matches(seq) and h(event):
                return True

        for h in self.keypress_event_post_hooks:
            if h(event):
                return
        return self._widgetKeyPressEvent(event)
