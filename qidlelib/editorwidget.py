from PyQt4.QtCore import QObject


try:
    from PyKDE4.kdecore import *
    from PyKDE4.kdeui import *
    from PyKDE4.kparts import *
    have_kate_part = True
except:
    from PyQt4.QtGui import QPlainTextEdit
    have_kate_part = False
    


class TextEditorWidget(QObject):
    def __init__(self,parent = None):
        super(TextEditorWidget,self).__init__(parent = parent)
        if have_kate_part:
            self.factory = KLibLoader.self().factory("katepart")
            self.part = self.factory.create(self, "KatePart")
            self._widget = self.part.widget()
        else:
            self._widget = QPlainTextEdit(parent)
            
        self.widget.setStyleSheet("""
            QFrame { border:none }
            QScrollBar:horizontal {
                width: 0px;
            }
        """)
    
    
    def content(self):
        if have_kate_part:
            return unicode(self.part.domDocument().toByteArray(),'utf-8')
        else:
            return self.widget.document().toPlainText()
    
    @property
    def widget(self):
        return self._widget
