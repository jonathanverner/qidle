from PIL import Image, ImageQt
from printhooks import PackedQImage

def pack(obj):
    pi = PackedQImage()
    pi.from_QImage(ImageQt.ImageQt(obj))
    return pi


def register_hooks(hooks):
    hooks.register_transport_hook(Image.Image, pack)


