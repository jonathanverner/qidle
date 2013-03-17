#!/usr/bin/python
# -*- coding: utf-8 -*-
# <Copyright and license information goes here.>
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QGraphicsLinearLayout, QApplication, QPlainTextEdit, QFont

from util import python_3
from shell import ShellManager, remoteShell
from console import Console

import sys

if __name__ == "__main__":
    shellManager = ShellManager(remoteShell)
    app = QApplication(sys.argv)
    app.setStyleSheet("""
      QPlainTextEdit { border:none; }
    """);
    edit = QPlainTextEdit()
    ubuntuMono = QFont("Ubuntu Mono",10)
    edit.setFont(ubuntuMono)
    console = Console(edit)
    edit.keyPressEvent = console.keyPressEvent
    edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    shellManager.waitingForInput.connect(console.do_readline)
    shellManager.write.connect(console.write)
    shellManager.finished_running.connect(console.finished_running)
    shellManager.shell_restarted.connect(console.shell_restarted)
    console.run_code.connect(shellManager.execute_code)
    console.read_line.connect(shellManager.sendInput)
    console.interrupt_shell.connect(shellManager.interrupt)
    console.restart_shell.connect(shellManager.restart_shell)
    console.get_completions = shellManager.get_completions
    app.lastWindowClosed.connect(shellManager.quit)
    edit.resize(600,500)
    edit.show()
    app.exec_()

else:
    
    from PyKDE4.plasma import Plasma
    from PyKDE4 import plasmascript

    class PythonShellApplet(plasmascript.Applet):
        def __init__(self,parent,args=None):
            plasmascript.Applet.__init__(self,parent)
 
        def init(self):
            self.setHasConfigurationInterface(False)
            self.setAspectRatioMode(Plasma.IgnoreAspectRatio)
            self.theme = Plasma.Svg(self)
            self.theme.setImagePath("widgets/background")
            self.setBackgroundHints(Plasma.Applet.DefaultBackground)
    
            self.layout = QGraphicsLinearLayout(Qt.Vertical, self.applet)
            self.editorWidget = Plasma.TextEdit(self.applet)
            self.editorWidget.nativeWidget().setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.console = Console(self.editorWidget.nativeWidget())
            self.console.allow_quit = False
            self.editorWidget.keyPressEvent = self.console.keyPressEvent
            self.shellManager = ShellManager()
            self.shellManager.waitingForInput.connect(self.console.do_readline)
            self.shellManager.write.connect(self.console.write)
            self.shellManager.finished_running.connect(self.console.finished_running)
            self.shellManager.shell_restarted.connect(self.console.shell_restarted)
            self.console.run_code.connect(self.shellManager.execute_code)
            self.console.read_line.connect(self.shellManager.sendInput)
            self.console.interrupt_shell.connect(self.shellManager.interrupt)
            self.console.restart_shell.connect(self.shellManager.restart_shell)
            self.console.completion_enabled = False
            self.layout.addItem(self.editorWidget)
            self.resize(300,500)
            
        def __del__(self):
            self.shellManager.quit()
        
    def CreateApplet(parent):
        return PythonShellApplet(parent)
