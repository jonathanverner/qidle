from PyQt4.QtGui import QWidget
from PyQt4.QtCore import pyqtSlot, QObject
import editorwidget as editor
from insulate.utils import signal

import logging
from insulate.debug import msg
logger = logging.getLogger(__name__)


class EditorTabs(QObject):
    file_closed = signal(str)
    tab_num_changed = signal()

    def __init__(self, tabwidget, parent=None):
        super(EditorTabs, self).__init__(parent)
        self.tabwidget = tabwidget
        self.tabs = {}
        self.next_tab_id = 0
        
    def own_tab(self, tab):
        return self._find_tab(tab) is not None
    
    @pyqtSlot()
    def open_file(self, fname=None):
        ed_id = self._find_tab(fname)
        if ed_id is not None:
            self.tabwidget.setCurrentWidget(self.tabs[ed_id].widget)
        else:
            tab_id = self.new_tab()
            self.tabs[tab_id].open_file(fname)
            
    def new_tab(self):
        tab_id = self.next_tab_id
        self.next_tab_id += 1
        code_editor = editor.get_editor_widget(self.tabwidget)
        code_editor.name_changed.connect_named(tab_id, self._tab_name_changed)
        self.tabs[tab_id] = code_editor
        index = self.tabwidget.addTab(code_editor.widget, code_editor.name)
        self.tabwidget.setCurrentIndex(index)
        self.tab_num_changed.emit()
        return tab_id
            
    def close_tab(self, tab_num):
        ed_id = self._find_tab(tab_num)
        assert ed_id is not None, "Closing tab not belonging to me"
        self.tabwidget.removeTab(tab_num)
        ed = self.tabs[ed_id]
        name = ed.path
        del self.tabs[ed_id]
        del ed
        self.file_closed.emit(name)
        self.tab_num_changed.emit()
            
    def show_cfg_dialog(self):
        editor.show_config_dialog(self.tabwidget)
        
    def _find_tab(self, tab_ident):
        if type(tab_ident) == 'str':
            # find filename tab
            pass
        elif type(tab_ident) == int:
            w = self.tabwidget.widget(tab_ident)
            for (tid, ed) in self.tabs.items():
                if ed.widget == w:
                    return tid
            return None
        else:
            return None
    
    def _index_of(self, obj):
        if type(obj) == int:
            return self.tabwidget.indexOf(self.tabs[obj].widget)
        elif type(obj) == QWidget:
            return self.tabwidget.indexOf(obj)
        else:
            return self.tabwidget.indexOf(obj.widget)

    def _tab_name_changed(self, tab_id, tab_name):
        logger.debug(msg("ID:", tab_id, "NAME:", tab_name))
        self.tabwidget.setTabText(self._index_of(tab_id), tab_name)
