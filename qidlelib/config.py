from os.path import expanduser
import json
import codecs

class configuration(object):
        
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
        return str(self.__dict__)
    
    def save_to_file(self):
        f = codecs.EncodedFile(open(expanduser("~/.qidlerc"),'w'), 'utf-8')
        json.dump(self.__dict__,f,indent=4, encoding='utf-8', ensure_ascii=False)
        f.close()
    
    def load_from_file(self):
        try:
            f = codecs.EncodedFile(open(expanduser("~/.qidlerc"), 'r'),'utf-8')
            self.__dict__ = json.load(f)
            return True
        except:
            return False
        
