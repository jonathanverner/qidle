from base64 import b64encode, b64decode
import logging
logger = logging.getLogger(__name__)

from matplotlib.figure import Figure

from printhooks import PackedQImage


def pack_figure(fig):
    logger.debug("Packing figure...")
    fig.set_facecolor('white')
    fig.canvas.draw()
    buf = fig.canvas.buffer_rgba(0,0)
    l, b, w, h = fig.bbox.bounds
    return PackedQImage(buf,w,h,format=PackedQImage.FORMAT_ARGB32)

def register_hooks(hooks):
    hooks.register_transport_hook(Figure, pack_figure)
