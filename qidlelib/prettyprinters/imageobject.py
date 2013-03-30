from PyQt4.QtGui import QImage, QTextDocument
from PyQt4.QtCore import QUrl, QByteArray, QVariant

class ImageObject(object):
    def __init__(self, data, id):
        self.type = 'image'
        self.format = 'png'
        self.data = data
        self.url = 'img:/'+id

    def __html_repr__(self, document = None):
        if document is not None:
            img = QImage()
            img.loadFromData(QByteArray(self.data))
            document.addResource(
                QTextDocument.ImageResource, QUrl(self.url), QVariant(img))
            return '<img src="' + self.url + '"/>'
        else:
            return repr(self)

