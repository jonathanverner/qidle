from code import InteractiveInterpreter
from rlcompleter import Completer
import sys, os

from insulate.utils import signal, SingleShotException, rpc

import logging
from insulate.debug import msg, filt
logger = logging.getLogger(__name__)

class SignalStream(object):
    write = signal()
    waiting_for_input = signal()
    flush = signal()
    close = signal()
    
    keyboard_interrupt = SingleShotException(KeyboardInterrupt)
    
    def __init__(self):
        self.write = signal()
        self.waiting_for_input = signal()
        self.flush = signal()
        self.close = signal()
        
        self._wait = signal()
        self.have_input = False

        
    def readline(self):
        logger.debug("Emitting waiting for input")
        self.waiting_for_input.emit()
        logger.debug("Emitted waiting for input")
        while not self.have_input:
            self._wait.emit()
        self.have_input = False
        return self.input
        
    def input_handler(self, str):
        logger.debug(msg("Got input", str))
        self.have_input = True
        self.input = str
    
    def interrupt(self):
        self.keyboard_interrupt.restart()
        self.write._raise_exception_on_emit(SignalStream.keyboard_interrupt)
        self.waiting_for_input._raise_exception_on_emit(SignalStream.keyboard_interrupt)
        self.flush._raise_exception_on_emit(SignalStream.keyboard_interrupt)
        self.close._raise_exception_on_emit(SignalStream.keyboard_interrupt)

class InsulatedShell(object):
    write_to_stream = signal(str,str)
    execute_finished = signal()
    waiting_for_input = signal()
    write_object = signal()
        
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
        
    def isolated_init(self):
        logger.debug("Shell connecting stdin _wait.")
        try:
            sys.stdin._wait.connect(self._wait)
        except Exception, e:
            logger.debug(msg("Unable to connect _wait:", e))
            
        
    def input_handler(self, string):
        logger.debug(msg("Got input", string))
        sys.stdin.input_handler(string)
        
    def execute(self, code):
        code = unicode(code)
        logger.debug("Running code")
        logger.debug("*"*30)
        logger.debug(code)
        logger.debug("*"*30)
        ret = self.interpreter.runsource(code+"\n")
        logger.debug(msg("Finished run, ret == ", ret))
        SignalStream.keyboard_interrupt.cancel()
        self.execute_finished.emit()
        
    def interrupt(self):
        sys.stdin.interrupt()
        sys.stderr.interrupt()
        sys.stdout.interrupt()
        self.msg_stream.interrupt()
        
    def _message_priority(self, message_name):
        if message_name == 'interrupt':
            return rpc.PRIORITY_INTERRUPT
        
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
    
    
