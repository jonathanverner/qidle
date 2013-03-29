#!/usr/bin/python
# -*- coding: utf-8 -*-
# <Copyright and license information goes here.>
import sys
import logging
from qidlelib.insulate.debug import msg
logger = logging.getLogger(__name__)

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QGraphicsLinearLayout

from PyKDE4.plasma import Plasma
from PyKDE4 import plasmascript

from qidlelib.qeventloop import QEventLoop
from qidlelib.insulate.factory import InsulatedFactory
from qidlelib.shellwidget import ShellWidget

class PythonShellApplet(plasmascript.Applet):
    def __init__(self,parent,args=None):
        plasmascript.Applet.__init__(self,parent)

    def init(self):
        logger.debug("Starting qidle...")
        event_loop = QEventLoop()
        self.factory = InsulatedFactory(event_loop = event_loop)
        self.factory.start()
        self.factory.start_event_loop()

        self.setHasConfigurationInterface(False)
        self.setAspectRatioMode(Plasma.IgnoreAspectRatio)
        self.theme = Plasma.Svg(self)
        self.theme.setImagePath("widgets/background")
        self.setBackgroundHints(Plasma.Applet.DefaultBackground)

        self.layout = QGraphicsLinearLayout(Qt.Vertical, self.applet)
        self.editorWidget = Plasma.TextEdit(self.applet)
        self.shell_widget = ShellWidget(self.factory,self.editorWidget.nativeWidget())
        self.shell_widget._disable_completion()
        self.editorWidget.nativeWidget().setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editorWidget.keyPressEvent = self.shell_widget.console_widget.keyPressEvent
        self.layout.addItem(self.editorWidget)
        self.resize(600,500)
        
    def __del__(self):
        self.shell_widget.quit()
        self.factory.terminate()
    
def CreateApplet(parent):
    return PythonShellApplet(parent)
