import logging
from debug import msg
logger = logging.getLogger(__name__)

from utils import signal
from factory import RemoteFactory

        
class test(object):
    hello = signal()
    
    def __init__(self, name = 'Joni'):
        self.name = name
        
    def greet_me(self):
        print "test.greet_me: Hello, ", self.name
        self.hello.emit(self.name)
        
    def greet(self, name):
        print "test.greet: Hello, ", name
        self.hello.emit(name)
        
    def readline(self):
        c = raw_input("Zadej jmeno:")
        print "Zadane jmeno je ", c
        self.hello.emit(c)
        
    def long_work(self):
        while True:
            try:
                self._process_interrupts()
            except:
                pass
        
        
def hello_handler(name):
    print "hello_handler: received signal, name == ", name
    
        
def testA():
    f = RemoteFactory()
    f.start()
    lt = f.create_object(test,"Jakub")
    lt.hello.connect(hello_handler)
    lt.greet_me()
    lt.greet("Joni")
    return f, lt
