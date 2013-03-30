class ImageObject(object):
    def __init__(self, data, id):
        self.type = 'image'
        self.format = 'png'
        self.data = data
        self.url = 'img:/'+id
