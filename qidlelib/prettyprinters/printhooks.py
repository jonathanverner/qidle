import imp
import logging
from os import path
logger = logging.getLogger(__name__)

class PrintHooks(object):
    def __init__(self):
        self.hooks = {}
        self.transport_hooks = {}

    def register_transport_hook(self, typ, hook):
        self.transport_hooks[typ] = hook

    def register_hook(self, typ, hook):
        self.hooks[typ] = hook

    def is_pretty_printable(self, obj):
        if self.has_html_repr_method(obj):
            return True
        if self._find_hook(obj) is not None:
            return True
        return False

    def has_html_repr_method(self, obj):
        return '__html_repr__' in dir(obj)

    def html_repr(self, obj, document = None):
        try:
            if self.has_html_repr_method(obj):
                return self.wrap(obj.__html_repr__(document))
            hook = self._find_hook(obj)
            if hook is not None:
                return self.wrap(hook(obj,document))
        except Exception, e:
            logger.warn("Encountered exception " + str(e) + " while pretty printing object " + str(obj))
        return repr(obj)

    def wrap(self, string):
        return '<html_snippet>'+string+'</html_snippet>'

    def pack_for_transport(self, obj):
        hook = self._find_hook(obj,_hooks=self.transport_hooks)
        if hook is not None:
            return hook(obj)
        else:
            return None

    def _try_load_hook(self,obj):
        try:
            package_path = path.dirname(__file__)
            mod_name = str(obj.__class__).replace('.','_').lstrip("<class '").rstrip("'>").strip()
            found = imp.find_module(mod_name, [package_path])
            mod = imp.load_module(mod_name,*found)
            mod.register_hooks(self)
            return True
        except Exception, e:
            logger.debug("Encountered exception " + str(e) + " while searching for hook for " + str(obj))
            return False

    def _find_hook(self, obj, _load_hook=True, _hooks=None):
        if _hooks is None:
            _hooks = self.hooks
        for (cls, hook) in _hooks.items():
            if isinstance(obj,cls):
                return hook
        if _load_hook:
            if self._try_load_hook(obj):
                return self._find_hook(obj, _load_hook=False, _hooks=_hooks)
        return None

print_hooks = PrintHooks()
