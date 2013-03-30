from PyQt4.QtGui import QTextDocument
from PyQt4.QtCore import QUrl, QVariant

from PIL import Image, ImageQt

pil_img_ids = 0
def get_url():
    url="img://PIL_Image_Image/"+str(pil_img_ids)
    pil_img_ids += 1
    return url

def html_repr(obj, document):
    if document is not None:
        img = ImageQt.ImageQt(obj)
        url = get_url()
        document.addResource(
            QTextDocument.ImageResource, QUrl(url), QVariant(img))
        return '<img src="' + url + '"/>'
    else:
        return repr(obj)

def register_hooks(hooks):
    hooks.register_hook(Image.Image, html_repr)


