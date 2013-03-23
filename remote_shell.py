from code import InteractiveInterpreter
from rlcompleter import Completer
import sys, os

from remote.utils import signal

import logging
from remote.debug import msg, filt
logger = logging.getLogger(__name__)
filt.enable_module(__name__)
filt.enable_module('remote.objects')
filt.enable_module('remote.utils')
filt.enable_module('remote.RemoteFactory')


class SignalStream(object):
    write = signal()
    waiting_for_input = signal()
    flush = signal()
    close = signal()
    
    def __init__(self):
        self.write = signal()
        self.waiting_for_input = signal()
        self.flush = signal()
        self.close = signal()
        
        self.__wait = signal()
        self.have_input = False

        
    def readline(self):
        self.waiting_for_input.emit()
        while not self.have_input:
            self.__wait.emit()
        self.have_input = False
        return self.input
        
    def input_handler(self, str):
        self.have_input = True
        self.input = str
        

class RemoteShell(object):
    write_to_stream = signal(str,str)
    execute_finished = signal()
    waiting_for_input = signal()
        
    def __init__(self, locals = None, filename=''):
        logger.debug("Shell initializing.")
        self.write_to_stream = signal(str,str)
        self.execute_finished = signal()
        
        self.locals = locals
        if not self.locals:
            self.locals = {}
        self.locals['__name__']=filename
        self.completer = Completer(self.locals)
        self.os = os
        self.locals['__shell__'] = self
        
        logger.debug("Shell initializing interpreter.")
        self.interpreter = InteractiveInterpreter(locals=self.locals)
        self.msg_stream = SignalStream()
        self.interpreter.write = self.msg_stream.write
        
        logger.debug("Shell redirecting streams.")
        sys.stdin = SignalStream()
        sys.stdout = SignalStream()
        sys.stderr = SignalStream()
        
        logger.debug("Shell connecting streams.")
        logger.debug("                  stdout.")
        sys.stdout.write.connect_named("stdout",self.write_to_stream)
        logger.debug("                  stderr.")
        sys.stderr.write.connect_named("stderr",self.write_to_stream)
        logger.debug("                  interpretter.")
        self.msg_stream.write.connect_named("msg",self.write_to_stream)
        logger.debug("                  stdin.")
        sys.stdin.waiting_for_input.connect(self.waiting_for_input)
        logger.debug("Shell streams connected.")
        
        logger.debug("Shell connecting stdin __wait.")
        try:
            sys.stdin.__wait.connect(self.__wait)
        except:
            pass
        logger.debug("Shell initialized.")
        
    def input_handler(self, string):
        self.stdin.input_handler(string)
        
    def execute(self, code):
        code = unicode(code)
        logger.debug("Running code")
        logger.debug("*"*30)
        logger.debug(code)
        logger.debug("*"*30)
        ret = self.interpreter.runsource(code+"\n")
        logger.debug(msg("Finished run, ret == ", ret))
        self.execute_finished.emit()
        
    def interrupt(self):
        raise KeyboardInterrupt
        
    def completion(self, prefix):
        ret = []
        i = 0
        cmpl = self.completer.complete(unicode(prefix),i)
        while cmpl is not None:
            ret.append(cmpl)
            i += 1
            cmpl = self.completer.complete(unicode(prefix),i)
            if i > 50:
                logger.debug("Too many completions, quitting ...")
                break
        return ret
