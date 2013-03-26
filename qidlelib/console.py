# -*- coding: utf-8 -*-
# <Copyright and license information goes here.>

from time import time
import os
import logging
from insulate.debug import msg, debug
logger = logging.getLogger(__name__)

from PyQt4 import QtCore
from PyQt4.QtCore import Qt, QEvent, QEventLoop, pyqtSignal, pyqtSlot, QUrl, QFileSystemWatcher, QObject, QDir, QTimer
from PyQt4.QtGui import QKeySequence, QKeyEvent, QCompleter, QTextCursor, QStringListModel, QFileSystemModel, QDirModel, QFileDialog, QFont

from idlelib.PyParse import Parser as PyParser
from insulate.utils import signal

from textblock import TextBlock, block_type_for_stream
from syntax import PythonHighlighter



class Console(QObject):
    
    @property
    def _currentCursor(self):
        return self.widget.textCursor()
    
    @_currentCursor.setter
    def _currentCursor(self, cursor):
        self.widget.setTextCursor( cursor )
        
    @property
    def _endCursor(self):
        return self._lastBlock.endCursor()
    
    @property
    def _currentBlock(self):
        return TextBlock(self._currentCursor)
    
    @property
    def _document(self):
        return self.widget.document()
    
    def _canDeletePreviousChar(self):
        if self._currentBlock.type in TextBlock.EDITABLE_TYPES and self._cursorInEditableArea():
            return self._currentBlock.containsCursor(self._currentCursor,in_active_area='strict')
        return False
    
    def _cursorInEditableArea(self, cursor = None):
        if cursor is None:
            cursor = self._currentCursor
        return self._lastBlock.isCursorInRelatedBlock(cursor) and self._currentBlock.containsCursor(cursor)
    
    def _canEditCurrentChar(self):
        if not self._currentBlock.type in TextBlock.EDITABLE_TYPES:
            return False
        if not self._currentBlock.containsCursor(self._currentCursor):
            return False
        
        
    def _gotoBlockStart(self):
        self._currentCursor = self._currentBlock.startCursor()
        
    def _gotoBlockEnd(self):
        self._currentCursor = self._currentBlock.endCursor()
        
    @property
    def _lastBlock(self):
        return TextBlock(self._document.lastBlock())
    
    def _gotoEnd(self):
        self._currentCursor = self._endCursor
        
    def _insertBlock(self, cursor = None, block_type = TextBlock.TYPE_CODE_CONTINUED, content = ""):
        if cursor is None:
            cursor = self._currentCursor
        b = TextBlock(cursor, create_new = True, typ = block_type)
        if len(content):
            b.appendText(content)
        return b
    
    def _appendBlock(self, block_type, content = "", html = False):
        b = TextBlock(self._endCursor, create_new = True, typ = block_type)
        if len(content) > 0:
            if html:
                b.appendHtml(content)
            else:
                b.appendText(content)
        return b
    
    def _joinCurrentToPreviousBlock(self):
        logger.debug(msg("Deleting current block"))
        cur = self._currentBlock
        prev = cur.previous()
        prev.appendText(cur.content())
        cur.deleteBlock()
        
    def wordUnderCursor(self):
        c = self._currentCursor
        return self._currentBlock.wordUnderCursor(self._currentCursor)
    
    def _guessStringPrefix(self, char):
        c = self._currentCursor
        block_content = self._currentBlock.content(include_decoration=True)
        pos = min(c.positionInBlock(), len(block_content))
        block_content = unicode(block_content[:pos]+char)
        
        double_quotes = block_content.count('"')
        single_quotes = block_content.count("'")
        
        if double_quotes % 2 == 0 and single_quotes % 2 == 0:
            return None
        
        stop_chars = '"\' '
        ret = []
        while pos >= 0 and block_content[pos] not in stop_chars:
            ret.append(block_content[pos])
            pos -=1
        ret.reverse()
        logger.debug(''.join(ret))
        return ''.join(ret)
        
        
        
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
        
    
    DEFAULT_INDENT = 4
    
    MODE_RUNNING = 0
    MODE_CODE_EDITING = 1
    MODE_RAW_INPUT = 2
    MODE_READ_ONLY = 3
    MODE_WAITING_FOR_INTERRUPT = 4
    
    #run_code = pyqtSignal(unicode)
    run_code = signal(unicode)
    read_line = signal(unicode)
    restart_shell = signal()
    interrupt_shell = signal()
    quit = pyqtSignal()
    
    def __init__(self, widget):
        super(Console,self).__init__()
        self.font_size = 10
        self.font = QFont("Ubuntu Mono",self.font_size)
        self.allow_quit = True
        self.indent = self.DEFAULT_INDENT
        self.widget = widget
        self.hilighter = PythonHighlighter(self.widget.document())
        self.parser = PyParser(self.indent, self.indent)
        
        self.widget.setFont(self.font)
        
        # The source file's we are watching
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self._sourceChanged)
        
        self._widgetKeyPressEvent = self.widget.keyPressEvent
        self.widget.keyPressEvent = self.keyPressEvent
        self._widgetFocusInEvent = self.widget.focusInEvent
        self.widget.focusInEvent = self.focusInEvent
        self.widget.dragEnterEvent = self.dragEnterEvent
        self.widget.dragMoveEvent = self.dragMoveEvent
        self.widget.dropEvent = self.dropEvent
        
        # Code Completion
        self.completer = QCompleter([kw for kw in PythonHighlighter.keywords if len(kw)>3])
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.activated.connect(self._insertCompletion)
        self.completer.popup().setStyleSheet("QWidget {border-width: 1px; border-color: black;}")
        self.completer.popup().setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.completer.setWidget(self.widget)
        self.completion_enabled = True
        
        self._lastBlock.setType(TextBlock.TYPE_MESSAGE)
        self._lastBlock.appendText("PyShell v 0.5: Starting ...")
        self.start_editing()
        
        # Restart shell timer
        self.timer = QTimer(self)
        
        

        
    
    @property
    def mode(self):
        return self._mode
    
    @pyqtSlot()
    def increase_font(self):
        self.font_size += 1
        self.font = QFont("Ubuntu Mono",self.font_size)
        self.widget.setFont(self.font)
        
    @pyqtSlot()
    def decrease_font(self):
        self.font_size -= 1
        self.font = QFont("Ubuntu Mono",self.font_size)
        self.widget.setFont(self.font)
    
    @pyqtSlot(unicode, unicode)
    def write(self, stream, string):
        assert self.mode == Console.MODE_RUNNING or self.mode == Console.MODE_WAITING_FOR_INTERRUPT, "Cannot write to console in "+str(self.mode) +" (need to be RUNNING/INTERRUPT mode) "
        if string.startswith('<html_snippet>'):
	    self._lastBlock.appendHtml(string.replace("<html_snippet>","").replace("</html_snippet>",""))
	else:	  
            lines = string.split('\n')
            block_type = block_type_for_stream(stream)
            for ln in lines[:-1]:
                self._lastBlock.appendText(ln)
                self._lastBlock.setType(block_type)
                self._appendBlock(block_type)
            self._lastBlock.appendText(lines[-1])
            self._gotoEnd()
    
    @pyqtSlot()
    def do_readline(self):
        assert self.mode != Console.MODE_RAW_INPUT, "Cannot call readline before previous call finished"
        assert self.mode == Console.MODE_RUNNING, "readline may be called only in the RUNNING mode"
        self._lastBlock.setType(TextBlock.TYPE_RAW_INPUT)
        self._mode = Console.MODE_RAW_INPUT
    
    @pyqtSlot()
    def shell_restarted(self):
        logger.debug("Shell restarted!")
        self._appendBlock(TextBlock.TYPE_MESSAGE,"<span style='color:green'>"+"="*20+"</span> SHELL RESTARTED <span style='color:green'>" + "="*20 +"</span>", html=True)
        self.start_editing()
        logger.debug("Shell restarted!")
        
    @pyqtSlot()
    def finished_running(self):
        if len(self._lastBlock.content()) == 0:
            self._lastBlock.deleteBlock()
        self.start_editing()
        
    @pyqtSlot()
    def start_editing(self):
        new_code_block = self._appendBlock(TextBlock.TYPE_CODE_START)
        self._gotoEnd()
        self._mode = Console.MODE_CODE_EDITING
        
    @pyqtSlot()
    def load_file_dlg(self):
        fname = QFileDialog.getOpenFileName(self.widget, "Watch a Python Source File", QDir.currentPath(), "Python Source Files (*.py)")
        self.watcher.addPath(fname)
        self.watcher.fileChanged.emit(fname)
        
    def _wantToSubmit(self):
        if self.parser.get_continuation_type():
            logger.debug(msg("Is continuation, returning False"))
            return False
        if self.parser.is_block_opener():
            logger.debug(msg("Is block opener, returning False"))
            return False
        cur_line_content = self._currentBlock.content()
        if len(cur_line_content) == cur_line_content.count(" "):
            logger.debug(msg("empty line, returning True"))
            return True
        if len(self.parser.get_base_indent_string()) == 0:
            logger.debug(msg("Base indent string is short, returning True "))
            return True
        logger.debug(msg("returning False"))
        return False
            
    def _process_enter(self):
        logger.debug(msg("running..."))
        # Apply History
        if not self._lastBlock.isCursorInRelatedCodeBlock(self._currentCursor) and not self._lastBlock.containsCursor(self._currentCursor):
            logger.debug(msg("applying history..."))
            if self._currentBlock.type in TextBlock.CODE_TYPES:
                hist = map(lambda x:x.content(),self._currentBlock.relatedCodeBlocks())
            else:
                hist = [self._currentBlock.activeContent()]
            cur_block = self._lastBlock
            cur_block.appendText(hist[0])
            if self.mode == Console.MODE_RAW_INPUT:
                typ = TextBlock.TYPE_RAW_INPUT
            else:
                typ = TextBlock.TYPE_CODE_CONTINUED
            for h in hist[1:]:
                    b = self._appendBlock(typ,h)
                    if typ == TextBlock.TYPE_RAW_INPUT:
                        b.first_input_block = cur_block
            self._gotoEnd()
        # Editing code 
        elif self.mode == Console.MODE_CODE_EDITING:
            # decide whether to run the code
            if self._lastBlock.containsCursor(self._currentCursor):
                logger.debug(msg("Deciding whether to run code..."))
                code = "\n".join(map(lambda x:x.content(),self._currentBlock.relatedCodeBlocks()))
                self.parser.set_str(code+"\n")
                if self._wantToSubmit():
                    self._mode = Console.MODE_RUNNING
                    self._appendBlock(TextBlock.TYPE_OUTPUT_STDOUT)
                    self.run_code.emit(code.rstrip()+"\n")
                else:
                    indent_string = self.parser.get_base_indent_string()
                    indent_level = indent_string.count("\t")
                    if self.parser.is_block_opener():
                        indent_level += 1
                    b = self._appendBlock(TextBlock.TYPE_CODE_CONTINUED," "*indent_string.count(" "))
                    b.indent( indent_level )
                    self._gotoEnd()
            # In the middle of the code, add a newline + indentation
            else:
                code = "\n".join(map(lambda x:x.content(),self._currentBlock.relatedCodeBlocks(only_previous=True)))
                self.parser.set_str(code+"\n")
                indent_string = self.parser.get_base_indent_string()
                indent_level = indent_string.count("\t")
                if self.parser.is_block_opener():
                    indent_level += 1
                b = self._insertBlock(self._currentCursor, block_type=TextBlock.TYPE_CODE_CONTINUED,content=" "*indent_string.count(" "))
                b.indent( indent_level )
                self._gotoBlockEnd()
        
        # Entering input
        elif self.mode == Console.MODE_RAW_INPUT:
            ret = "\n".join(map(lambda x:x.activeContent(),self._currentBlock.relatedInputBlocks()))
            self._appendBlock(TextBlock.TYPE_OUTPUT_STDOUT)
            self._mode = Console.MODE_RUNNING
            self.read_line.emit(ret)
        
        logger.debug(msg("finished."))
        
    def _process_completion_widget(self, event):
        if self.completer.popup().isVisible():
            if event.key() in [ Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Up, Qt.Key_Down ]:
                event.ignore()
                return True
            elif event.key() in [ Qt.Key_Home ]:
                self.completer.popup().hide()
        return False

    def focusInEvent(self, event):
        self.completer.setWidget(self.widget)
        self._widgetFocusInEvent(event)
        
    def _restart_shell_from_interrupt(self):
        self.timer.stop()
        if self._mode == Console.MODE_WAITING_FOR_INTERRUPT:
            logger.debug("Restarting shell, since it did not respond to interrupt")
            self.restart_shell.emit()
        
    def keyPressEvent(self, event):
        
        # Ctrl-C Handling
        if event.matches(QKeySequence.Copy):
            if ( self._currentCursor.selection().isEmpty and ( self.mode == Console.MODE_RUNNING or self.mode == Console.MODE_RAW_INPUT ) ):
                self._mode = Console.MODE_WAITING_FOR_INTERRUPT
                self.timer.timeout.connect(self._restart_shell_from_interrupt)
                self.timer.start(1000)
                self.interrupt_shell.emit()
        
        # Ctrl-Q Handling
        if event.matches(QKeySequence.Quit):
            if self.allow_quit:
                self.quit.emit()
                #logger.debug(msg("Quitting ..."))
                #self.widget.close()
                event.ignore()
            return
        
        # Ctrl-+/- Handling
        if event.matches(QKeySequence.ZoomIn):
            self.increase_font()
            return
        if event.matches(QKeySequence.ZoomOut):
            self.decrease_font()
        
        # Ctrl-O Handling
        if event.matches(QKeySequence.Open) and self.mode == Console.MODE_CODE_EDITING:
            self.load_file_dlg()
            event.ignore()
            return
        
        # No editing allowed in read only mode
        elif self.mode == Console.MODE_READ_ONLY:
            if event.key() in [ Qt.Key_Return, Qt.Key_Backspace, Qt.Key_Delete ] or len(event.text()) != 0:
                event.ignore()
                return
        
        # Nothing allowed when the shell is running or waiting for interrupt
        elif self.mode in [ Console.MODE_RUNNING, Console.MODE_WAITING_FOR_INTERRUPT ]:
            event.ignore()
            return
            
        # Completer widget is shown, delegate to completer
        elif self._process_completion_widget(event):
            return
        
        # Enter
        elif event.key() == Qt.Key_Return:
            self._process_enter()
            return
        
        # BackSpace
        elif event.key() == Qt.Key_Backspace:
            if self.mode == Console.MODE_CODE_EDITING:
                # If in leading position
                if self._currentBlock.isInLeadingPosition(self._currentCursor):
                    # no indent present, join with previous block
                    if self._currentBlock.indentLevel() == 0:
                        if self._currentBlock.type == TextBlock.TYPE_CODE_CONTINUED:
                            self._joinCurrentToPreviousBlock()
                            return
                        event.ignore()
                        return
                    # unindent the current line
                    else:
                        self._currentBlock.unIndent()
                        return
            # prevent deleting inactive characters
            if not self._canDeletePreviousChar():
                event.ignore()
                return

        # HOME 
        elif event.matches(QKeySequence.MoveToStartOfLine):
            self._currentCursor = self._currentBlock.leadingCursor()
            return
        elif event.key() == Qt.Key_Home and (event.modifiers() & Qt.ShiftModifier):
            c = self._currentCursor
            self._currentBlock.cursorSelectToLeadingPosition(c)
            self._currentCursor = c
            return
        
        # LEFT, UP, DOWN ...
        # elif event.matches(QKeySequence.MoveToPreviousChar):
        elif event.key() == Qt.Key_Left and not self._currentBlock.containsCursor(self._currentCursor, in_active_area = 'strict'):
            event.ignore()
            return
        
        # Ctrl-UP
        elif event.key() == Qt.Key_Up and (event.modifiers() & Qt.ControlModifier):
            prev = self._currentBlock.firstSameBlock()
            if not prev.isFirst():
                prev = prev.previous().firstSameBlock()
            self._currentCursor = prev.cursorAt( self._currentCursor.positionInBlock() )
        
        # Ctrl-Down
        elif event.key() == Qt.Key_Down and (event.modifiers() & Qt.ControlModifier):
            next = self._currentBlock.lastSameBlock()
            if not next.isLast():
                next = next.next()
            self._currentCursor = next.cursorAt( self._currentCursor.positionInBlock() )
        
        # DELETE KEY
        # Prevent Editing of Noneditable blocks
        elif (not self._currentBlock.type in TextBlock.EDITABLE_TYPES or not self._cursorInEditableArea()):
            if len(event.text()) != 0:
                self._gotoEnd()
                #event.ignore()
                #return
            
        # Code Completion
        elif (self.completion_enabled) and ((self.mode == Console.MODE_CODE_EDITING or self.mode == Console.MODE_RAW_INPUT) and len(event.text()) != 0):
            completion_prefix = self.wordUnderCursor() + event.text()
            in_string_prefix = self._guessStringPrefix(event.text())
            len_or_dot = len(completion_prefix) >= 3 or event.text() == '.'
        
            if (len_or_dot and unicode(completion_prefix[-1]) not in TextBlock.WORD_STOP_CHARS and len(event.text()) > 0) or in_string_prefix is not None:
                try:
                    # Filename completion when in string
                    if in_string_prefix is not None:
                        logger.debug(msg("Filename completion"))
                        model = QDirModel()
                        #model = QFileSystemModel()
                        #logger.debug(msg("Current Path:", QDir.currentPath()))
                        #model.setRootPath(QDir.currentPath())
                        if len(in_string_prefix) == 0 or not in_string_prefix[0] == os.sep:
                            in_string_prefix = unicode(QDir.currentPath()+QDir.separator()+ in_string_prefix)
                        logger.debug(msg("prefix", in_string_prefix))
                        self.completer.setModel(model)
                        self.completer.setCompletionPrefix(in_string_prefix)
                    # Otherwise we do normal code completion
                    else:
                        logger.debug(msg("Getting code completions for ", completion_prefix, "..."))
                        completions = self.get_completions(completion_prefix, _timeout = 1, _default = [])
                        logger.debug(msg("Got completions:", ','.join(completions)))
                        model = QStringListModel(completions)
                        self.completer.setModel(model)
                        self.completer.setCompletionPrefix(completion_prefix)
                    self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0,0))
                except Exception, e:
                    logger.debug(msg("Exception when completing:", str(e)))
                    if completion_prefix != self.completer.completionPrefix():
                        self.completer.setCompletionPrefix(completion_prefix)
                        self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0,0))
                cursor_rect = self.widget.cursorRect()
                cursor_rect.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(cursor_rect)
            else:
                self.completer.popup().hide()
                self.widget.clearFocus()
                self.widget.setFocus(Qt.ActiveWindowFocusReason)
                
        return self._widgetKeyPressEvent(event)
    
    def dragEnterEvent(self, e):
        file_url = QUrl(e.mimeData().text())
        if file_url.isValid() and file_url.isLocalFile():
            e.acceptProposedAction()
        else:
            e.ignore()
    
    def dragMoveEvent(self, e):
        pass
            
        
    def dropEvent(self, e):
        logger.debug(msg("Drag drop event"))
        file_url = QUrl(e.mimeData().text())
        if file_url.isValid() and file_url.isLocalFile():
            fname = file_url.toLocalFile()
            if fname in self.watcher.files():
                logger.debug(msg("already watching file", fname))
            else:
                logger.debug(msg("adding new file", fname))
                self.watcher.addPath(file_url.toLocalFile())
                logger.debug(msg("emmiting file changed signal"))
                self.watcher.fileChanged.emit(fname)
    
    @pyqtSlot(str)    
    def _sourceChanged(self, fname):
        logger.debug(msg(fname))
        if self._mode == Console.MODE_CODE_EDITING:
            self._appendBlock(TextBlock.TYPE_MESSAGE,content="Reloading file " + os.path.basename(unicode(fname)) + " and changing dir to " + os.path.dirname(unicode(fname)))
            self._appendBlock(TextBlock.TYPE_OUTPUT_STDOUT)
            self._mode = Console.MODE_RUNNING
            self.run_code.emit(unicode("execfile('"+fname+"')\n"))
            self.run_code.emit(unicode("__shell__.os.chdir(__shell__.os.path.dirname('"+fname+"'))\n"))
            logger.debug(msg("Changing to directory", os.path.dirname(unicode(fname))))
            os.chdir(os.path.dirname(unicode(fname)))
        else: 
            logger.debug(msg("Ignoring change, because not in CODE EDITING MODE", fname))
