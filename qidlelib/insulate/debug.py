import sys

import logging
from logging import StreamHandler
import sys


class Filter(object):
    def __init__(self, enabled_modules=[], disabled_funcs=[]):
        self.enabled_modules = enabled_modules
        self.disabled_funcs = disabled_funcs

    def enable_module(self, mod):
        if mod not in self.enabled_modules:
            self.enabled_modules.append(mod)

    def disable_function(self, func):
        if func not in self.disabled_funcs:
            self.disabled_funcs.append(func)

    def disable_module(self, mod):
        if mod in self.enabled_modules:
            self.enabled_modules.remove(mod)

    def enable_function(self, func):
        if func in self.disabled_funcs:
            self.disabled_funcs.remove(func)

    def filter(self, record):
        if record.levelno == logging.DEBUG:
            found = False
            for m in self.enabled_modules:
                try:
                    if record.module.endswith(m):
                        found = True
                except:
                    pass
            if not found:
                return 0
            for f in self.disabled_funcs:
                if record.funcName.endswith(f):
                    return 0
        return 1

enabled_mods = ['__main__', 'console', 'insulatedshell', 'printhooks', 'matplotlib_figure_Figure', 'editorwidget','qidle','editortabs']
disabled_funcs = ['router._send', 'router._recv', '__init__']
filt = Filter(enabled_modules=enabled_mods, disabled_funcs=disabled_funcs)
formatter = logging.Formatter(fmt = "%(name)s (PID %(process)d ): %(levelname)s %(filename)s:%(lineno)d:%(funcName)s: %(message)s")
handler = StreamHandler(stream = sys.__stderr__)
handler.addFilter(filt)
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)

root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.DEBUG)

#logging.basicConfig( stream = sys.__stderr__, format = "%(name)s (PID %(process)d ): %(levelname)s %(module)s.%(funcName)s: %(message)s" )
logger = logging.getLogger(__name__)


def msg(*args):
    ret = ""
    for a in args:
        try:
            ret += str(a)
        except Exception, e:
            ret += "msg::Exception:" + str(e)
        ret += ' '
    return ret


def debug(*args):
    for a in args:
        try:
            sys.__stdout__.write(str(a))
        except Exception, e:
            sys.__stdout__.write("Debug::Exception:" + str(e))
        sys.__stdout__.write(' ')
    sys.__stdout__.write("\n")
