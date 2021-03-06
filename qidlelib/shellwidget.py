import logging
from insulate.debug import msg, filt
logger = logging.getLogger(__name__)

from PyQt4.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QDir
from PyQt4.QtGui import QPlainTextEdit, QFont, QFileDialog

from console import Console
from insulate.utils import disconnect_object_signals, signal
from insulatedshell import InsulatedShell
from config import config


class ShellWidget(QObject):
    quit_signal = pyqtSignal()
    file_watched = signal(unicode)

    def __init__(self, factory, editor_widget):
        super(QObject, self).__init__()
        self.factory = factory
        self.shell = None
        self.edit = editor_widget

        self._construct_widget()
        self.start_shell()

    @property
    def editor_widget(self):
        return self.edit

    @property
    def console_widget(self):
        return self.console

    def _construct_widget(self):
        self.ubuntuMonoFont = QFont("Ubuntu Mono", 10)
        self.edit.setFont(self.ubuntuMonoFont)
        self.console = Console(self.edit)
        self.edit.keyPressEvent = self.console.keyPressEvent
        self.edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.console.quit.connect(self.quit)

    def _connect_shell(self):
        self.shell.waiting_for_input.connect(self.console.do_readline)
        self.shell.write_to_stream.connect(self.console.write)
        self.shell.execute_finished.connect(self.console.finished_running)
        self.shell.write_object.connect(self.console.write_object)
        self.shell.command_stream.connect(self.console.exec_command)

        self.console.run_code.connect(self.shell.execute)
        self.console.read_line.connect(self.shell.input_handler)
        self.console.interrupt_shell.connect(self.shell.interrupt)
        self.console.get_completions = self.shell.completion
        self.console.get_docs = self.shell.doctext
        self.console.get_f_sign = self.shell.function_signature
        self.console.get_import_completions = self.shell.import_completion
        self.console.get_dict_completions = self.shell.dict_completion
        self.console.restart_shell.connect(self.restart_shell)
        self.console.file_watched.connect(self.file_watched)

    def _disconnect_shell(self):
        disconnect_object_signals(self.console)
        disconnect_object_signals(self.shell)

    def kill_shell(self):
        if self.shell is not None:
            self._disconnect_shell()
            self.shell.terminate()

    def start_shell(self):
        self.shell = self.factory.create_object(InsulatedShell)
        self._connect_shell()

    def restart_shell(self):
        logger.debug("Restarting shell ...")
        self.kill_shell()
        self.start_shell()
        self.console.shell_restarted()
        logger.debug("Shell restarted ...")

    def _disable_completion(self):
        self.console.completion_enabled = False

    @pyqtSlot()
    def watch_file(self, fname=None):
        logger.debug(msg("Watching file ... ", fname))
        if fname is None:
            fname = QFileDialog.getOpenFileName(self.console.widget,
                                                "Watch a Python Source File",
                                                QDir.currentPath(),
                                                "Python Source Files (*.py)")
        self.console.watch_file(fname)

    def unwatch_file(self, fname):
        self.console.unwatch_file(fname)

    def quit(self):
        if config.history:
            self.console.save_history()
        self.kill_shell()
        self.quit_signal.emit()
