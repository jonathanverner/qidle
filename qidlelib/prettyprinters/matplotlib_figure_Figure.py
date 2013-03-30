from PyQt4.QtGui import QImage, QTextDocument
from PyQt4.QtCore import QUrl, QByteArray, QVariant

from matplotlib.figure import Figure


ids = 0
def get_url():
    url="img://matplotlib_figure_Figure/"+str(ids)
    ids += 1
    return url

class packed_fig(object):
    def __init__(self, fig):
        fig.canvas.draw()
        self.buf = fig.canvas.buffer_rgba(0,0)
        self.l, self.b, self.w, self.h = fig.bbox.bounds

def pack_figure(obj):
    return packed_fig(obj)

def figure_repr(obj, document):
    if document is not None:
        fg = packed_fig(obj)
        return packed_fig_repr(fg, document)
    else:
        return repr(obj)

def packed_fig_repr(obj, document):
    if document is not None:
        img = QImage(obj.buf, obj.w, obj.h, QImage.Format_ARGB32)
        url = get_url()
        document.addResource(
            QTextDocument.ImageResource, QUrl(url), QVariant(img))
        return '<img src="' + url + '"/>'
    else:
        return repr(obj)

def register_hooks(hooks):
    hooks.register_hook(Figure, figure_repr)
    hooks.register_hook(packed_fig, packed_fig_repr)
    hooks.register_transport_hook(Figure, pack_figure)
