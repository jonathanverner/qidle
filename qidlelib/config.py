from os.path import expanduser
import json
import codecs


class configuration(object):
    history = True
    history_file = "~/.qidle_history"
    history_size = 1000

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def keys(self):
        return self.__dict__.keys()

    def items(self):
        return self.__dict__.items()

    def __str__(self):
        return json.dumps(self.__dict__, indent=4, encoding='utf-8')

    def save(self, fpath=expanduser("~/.qidlerc")):
        f = codecs.EncodedFile(open(fpath, 'w'), 'utf-8')
        json.dump(self.__dict__, f, indent=4,
                  encoding='utf-8', ensure_ascii=False)
        f.close()

    def load(self, fpath=expanduser("~/.qidlerc")):
        try:
            f = codecs.EncodedFile(open(fpath, 'r'), 'utf-8')
            self.__dict__ = json.load(f)
            return True
        except:
            return False


config = configuration()
config.load()
