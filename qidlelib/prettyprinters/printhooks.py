import imp
import logging
from os import path
logger = logging.getLogger(__name__)

from base64 import b64encode, b64decode

from PyQt4.QtGui import QImage, QTextDocument
from PyQt4.QtCore import QUrl, QVariant, QByteArray, QBuffer, QIODevice

class PackedQImage(object):
    next_id = 0
    FORMAT_PNG = 0
    FORMAT_ARGB32 = 1

    def __init__(self, buf='', w=None, h=None, format=None):
        self.buf = b64encode(buf)
        self.format = format
        self.w = w
        self.h = h

    def from_QImage(self, img):
        buf = QByteArray()
        bf = QBuffer(buf)
        bf.open(QIODevice.WriteOnly)
        img.save(bf, format='PNG')
        self.buf = b64encode(buf.data())
        self.format = PackedQImage.FORMAT_PNG

    def to_QImage(self):
        if self.format == PackedQImage.FORMAT_ARGB32:
            return QImage(b64decode(self.buf), self.w, self.h, QImage.Format_ARGB32)
        elif self.format == PackedQImage.FORMAT_PNG:
            img = QImage()
            img.loadFromData(b64decode(self.buf), format='PNG')

    def _get_url(self):
        url="img://packed_qimage/"+str(PackedQImage.next_id)
        PackedQImage.next_id += 1
        return url

    def __html_repr__(self, document):
        if document is not None:
            logger.debug("Showing packed QImage...")
            url = self._get_url()
            img = self.to_QImage()
            document.addResource(
                QTextDocument.ImageResource, QUrl(url), QVariant(img))
            logger.debug('<img src="' + url + '"/>')
            return '<img src="' + url + '"/>'

def pack_qimage(obj):
    pi = PackedQImage()
    pi.from_QImage(obj)
    return pi

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
        if self._find_hook(obj,_hooks=self.transport_hooks) is not None:
            return True
        return False

    def needs_packing(self, obj):
        if self._find_hook(obj,_hooks=self.transport_hooks) is not None:
            return True
        return False

    def has_html_repr_method(self, obj):
        return '__html_repr__' in dir(obj)

    def html_repr(self, obj, document = None):
        try:
            if self.has_html_repr_method(obj):
                return self.wrap(obj.__html_repr__(document))
            logger.debug("Trying to load a html_repr hook for obj " + obj.__class__.__name__ + " in module "+obj.__class__.__module__ + " (obj is of type "+ str(type(obj))+")")
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
            #mod_name = str(obj.__class__).replace('.','_').lstrip("<class '").rstrip("'>").strip()
            #mod_name = str(obj.__class__.__module__).replace('.','_')+'_'+obj.__class__.__name__
            mod_name = str(obj.__class__.__module__).replace('.','_')+'_'+obj.__class__.__name__
            logger.debug("Trying to load module " + mod_name )
            found = imp.find_module(mod_name, [package_path])
            mod = imp.load_module(mod_name,*found)
            mod.register_hooks(self)
            logger.debug("Found " + mod_name )
            return True
        except Exception, e:
            logger.debug("Encountered exception " + str(e) + " while searching for hook for type " + str(obj.__class__))
        try:
            mod_name = str(obj.__class__.__module__)
            logger.debug("Trying to load module " + mod_name )
            found = imp.find_module(mod_name, [package_path])
            mod = imp.load_module(mod_name,*found)
            mod.register_hooks(self)
            logger.debug("Success")
            return True
        except Exception, e:
            logger.debug("Encountered another exception " + str(e) + " while searching for hook for " + str(obj))
        return False

    def _find_hook(self, obj, _load_hook=True, _hooks=None):
        if _hooks is None:
            _hooks = self.hooks
        logger.debug("Trying to find hook for obj " + obj.__class__.__name__ + " in module "+obj.__class__.__module__ + " (obj is of type "+ str(type(obj))+")")
        for (cls, hook) in _hooks.items():
            logger.debug("Checking hook ... " + cls.__name__ + " in module " + cls.__module__)
            if isinstance(obj,cls):
                logger.debug("Found hook for " + cls.__name__)
                return hook
            elif obj.__class__.__name__ == cls.__name__ and obj.__class__.__module__ == cls.__module__:
                logger.warn("Found hook for " + cls.__name__ + " but object is not an instance???")
                return hook
            logger.debug("Hook not suitable")
        if _load_hook:
            if self._try_load_hook(obj):
                return self._find_hook(obj, _load_hook=False, _hooks=_hooks)
        return None

import sys
sys.path.append(path.dirname(__file__))

print_hooks = PrintHooks()
print_hooks.register_transport_hook(QImage, pack_qimage)
