from PyQt4.QtGui import QImage

from printhooks import PackedQImage

def pack(obj):
    pi = PackedQImage()
    pi.from_QImage(obj)
    return pi


def register_hooks(hooks):
    hooks.register_transport_hook(QImage, pack)
