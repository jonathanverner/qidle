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
        if fname is not None:
            ed_id = self._find_tab(fname)
            if ed_id is not None:
                self.tabwidget.setCurrentWidget(self.tabs[ed_id].widget)
        else:
            tab_id = self.new_tab()
            self.tabs[tab_id].open_file(fname)

    @pyqtSlot()
    def save_tab(self, tabnum = None):
        """ Saves the tab @tabnum. If tabnum is None, saves the current tab.
            Returns True if successful, otherwise returns False

            Note: the tab must be an editor tab.
        """
        ed = self._find_editor(tabnum)
        if ed is None:
            return False
        return ed.save()

    @pyqtSlot()
    def saveas_tab(self, tabnum = None):
        """ Saves the tab @tabnum into a new file. If tabnum is None, saves the current tab.
            Returns True if successful, otherwise returns False

            Note: the tab must be an editor tab.
        """
        ed = self._find_editor(tabnum)
        if ed is None:
            return False
        return ed.save_as()

    @property
    def current_tab(self):
        """ Returns the editor id (in the self.tabs dictionary)
            of the current tab or None, if the current tab is not
            an editor tab.
        """
        return self._find_tab(None)

    @property
    def current_tab_number(self):
        """ Returns the number of the current tab. """
        return self.tabwidget.currentIndex()

    def new_tab(self,content=""):
        """ Opens a new tab populating it with content @content.

            Returns the id of the new tab.
        """
        tab_id = self.next_tab_id
        self.next_tab_id += 1
        code_editor = editor.get_editor_widget(self.tabwidget)
        code_editor.name_changed.connect_named(tab_id, self._tab_name_changed)
        if type(content) in [str,unicode]:
            code_editor.content = content
        self.tabs[tab_id] = code_editor
        index = self.tabwidget.addTab(code_editor.widget, code_editor.name)
        self.tabwidget.setCurrentIndex(index)
        self.tab_num_changed.emit()
        return tab_id

    def close_tab(self, tab_num = None, force=False):
        """ Closes the tab number @tab_num. Before closing the tab, it
            tries to save its contents. If this fails and @force is False,
            it doesn't do anything, and returns False. If the save is
            successful or @force is True, it closes the tab.

            Note: The tab must be an editor tab.
        """
        if tab_num is None:
            tab_num = self.current_tab_number
        ed_id = self._find_tab(tab_num)
        assert ed_id is not None, "Closing tab not belonging to me"
        ed = self.tabs[ed_id]
        if not ed.close() and not force:
            return False
        self.tabwidget.removeTab(tab_num)
        name = ed.path
        del self.tabs[ed_id]
        del ed
        self.file_closed.emit(name)
        self.tab_num_changed.emit()
        return True

    def show_cfg_dialog(self):
        editor.show_config_dialog(self.tabwidget)

    def _find_editor(self, tab_ident=None):
        """ Returns the editor id (in the self.tabs dictionary)
            of the tab identified by @tab_ident. The identification
            is the same as may be passed to _find_tab.

            If the tab does not exists or is not an editor tab,
            returns None.
        """
        ed_id = self._find_tab(tab_ident)
        if ed_id is None:
            return None
        else:
            return self.tabs[ed_id]

    def _find_tab(self, tab_ident=None):
        """ Returns the editor id (in the self.tabs dictionary)
            of the tab identified by @tab_ident. The identification
            @tab_ident may be either

               -- the number of the tab
               -- a filename
               -- None (in which case the current tab is returned)

            If the tab does not exists or is not an editor tab,
            returns None.
        """
        if tab_ident is None:
            tab_ident = self.current_tab_number

        if type(tab_ident) == 'str':
            for (tid, ed) in self.tabs.items():
                if ed.path == tab_ident or ed.name == tab_ident:
                    return tid
            return None
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
