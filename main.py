#!/usr/bin/python
# -*- coding: utf-8 -*-
# <Copyright and license information goes here.>
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QGraphicsLinearLayout, QApplication, QPlainTextEdit, QFont, QMenu, QMainWindow, QMenuBar

from qidle.console import Console
from remote_shell import RemoteShell
from remote.factory import RemoteFactory

import sys

import logging
from debug import msg
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    
    logger.debug("Starting qidle...")
    f = RemoteFactory()
    f.start()
    rs = f.create_object(RemoteShell)
    
    app = QApplication(sys.argv)
    app.setStyleSheet("""
      QPlainTextEdit { border:none; }
    """);
    
    main = QMainWindow()
    menubar = QMenuBar()
    main.setMenuBar(menubar)
    main.setWindowTitle(main.tr("Q-Idle Python Shell"))
    menus = {'File':QMenu(main.tr("&File")),
             'Shell':QMenu(main.tr("&Shell")),
             'Edit':QMenu(main.tr("&Edit")),
             'View':QMenu(main.tr("&View")),
             'Settings':QMenu(main.tr("&Settings")),
             'Help':QMenu(main.tr("&Help")),
             }
    
    open_file_action = menus['File'].addAction(main.tr("&Load File"))
    quit_action = menus['File'].addAction(main.tr("&Quit"))
    restart_shell_action = menus['Shell'].addAction(main.tr("&Restart Shell"))
    increase_font = menus['View'].addAction(main.tr("&Increase Font Size"))
    decrease_font = menus['View'].addAction(main.tr("&Decrease Font Size"))
    for m in ['File','Edit','View','Shell','Settings','Help']:
        menubar.addMenu(menus[m])
    
    edit = QPlainTextEdit()
    ubuntuMono = QFont("Ubuntu Mono",10)
    edit.setFont(ubuntuMono)
    console = Console(edit)
    edit.keyPressEvent = console.keyPressEvent
    edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    rs.waiting_for_input.connect(console.do_readline)
    rs.write_to_stream.connect(console.write)
    rs.execute_finished.connect(console.finished_running)
    
    console.run_code.connect(rs.execute)
    console.read_line.connect(rs.input_handler)
    console.interrupt_shell.connect(rs.interrupt)
    console.get_completions = rs.completion
    main.setCentralWidget(edit)
    console.quit.connect(rs.terminate)
    console.quit.connect(app.closeAllWindows)
    
    open_file_action.triggered.connect(console.load_file_dlg)
    restart_shell_action.triggered.connect(rs.interrupt)
    quit_action.triggered.connect(console.quit)
    increase_font.triggered.connect(console.increase_font)
    decrease_font.triggered.connect(console.decrease_font)
    
    app.lastWindowClosed.connect(rs.terminate)
    app.lastWindowClosed.connect(f.destroy)
    main.resize(600,500)
    #edit.show()
    main.show()
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
