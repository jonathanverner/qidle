from code import InteractiveInterpreter
from rlcompleter import Completer
import inspect
import sys
import os
import imp

from insulate.utils import signal, SingleShotException, rpc
from prettyprinters.printhooks import print_hooks
from packagecomplete import find_packages

import logging
from insulate.debug import msg, filt
#import savestate
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
        self.waiting_for_input._raise_exception_on_emit(
            SignalStream.keyboard_interrupt)
        self.flush._raise_exception_on_emit(SignalStream.keyboard_interrupt)
        self.close._raise_exception_on_emit(SignalStream.keyboard_interrupt)


class InsulatedShell(object):
    write_to_stream = signal(str, str)
    execute_finished = signal()
    waiting_for_input = signal()
    write_object = signal()
    command_stream = signal()

    def __init__(self, locals=None, filename=''):
        logger.debug("Shell initializing.")
        self.write_to_stream = signal(str, str)
        self.execute_finished = signal()
        self.waiting_for_input = signal()
        self.write_object = signal()

        self.locals = locals
        if not self.locals:
            self.locals = {}
        self.locals['__name__'] = filename
        self.completer = Completer(self.locals)
        self.packages = find_packages()
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
        sys.stdout.write.connect_named("stdout", self.write_to_stream)
        logger.debug("                  stderr.")
        sys.stderr.write.connect_named("stderr", self.write_to_stream)
        logger.debug("                  interpretter.")
        self.msg_stream.write.connect_named("msg", self.write_to_stream)
        logger.debug("                  stdin.")
        sys.stdin.waiting_for_input.connect(self.waiting_for_input)
        logger.debug("Shell streams connected.")

        sys.displayhook = self.display_hook

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
        logger.debug("*" * 30)
        logger.debug(code)
        logger.debug("*" * 30)
        ret = self.interpreter.runsource(code + "\n")
        logger.debug(msg("Finished run, ret == ", ret))
        SignalStream.keyboard_interrupt.cancel()
        self.execute_finished.emit()

    def interrupt(self):
        sys.stdin.interrupt()
        sys.stderr.interrupt()
        sys.stdout.interrupt()
        self.msg_stream.interrupt()


    def display_hook(self, obj):
        try:
            if obj is None:
                return
            if print_hooks.is_pretty_printable(obj):
                if print_hooks.needs_packing(obj):
                    packed = print_hooks.pack_for_transport(obj)
                    if not self.write_object.emit(packed):
                        logger.debug(msg("error sending packed object"))
                        sys.stdout.write(print_hooks.html_repr(obj))
                else:
                    if not self.write_object.emit(obj):
                        logger.debug(msg("error sending object"))
                        logger.debug(msg("error sending packed object"))
                        sys.stdout.write(print_hooks.html_repr(obj))
            else:
                logger.debug(msg("object", obj, "is not prettyprintable"))
                sys.stdout.write(repr(obj))
            return
        except Exception, e:
            logger.debug(msg("Exception", e, "encountered while printing object", obj))
            sys.__displayhook__(obj)


    def _message_priority(self, message_name):
        if message_name == 'interrupt':
            return rpc.PRIORITY_INTERRUPT

    def completion(self, prefix):
        ret = []
        i = 0
        cmpl = self.completer.complete(unicode(prefix), i)
        while cmpl is not None:
            ret.append(cmpl)
            i += 1
            cmpl = self.completer.complete(unicode(prefix), i)
            if i > 100:
                logger.debug("Too many completions, quitting ...")
                break
        return ret

    def import_completion(self, prefix):
        logger.debug("Getting import completions for '"+prefix+"'")
        ret = []
        for c in self.packages:
            if c.startswith(prefix):
                ret.append(c)
        logger.debug(msg("Got",len(ret),"completions, first 10:", ','.join(ret[:10])))
        return ret

    def dict_completion(self, dict_name, key):
        logger.debug("Getting dict completions for '"+dict_name+"' with prefix '"+key+"'")
        try:
            return [str(x) for x in eval(dict_name+'.keys()',self.locals, self.locals) if str(x).startswith(key)]
        except Exception, e:
            logger.debug(msg("Exception ",e," when getting dict completions for '"+dict_name+"' with prefix '"+key+"'"))
            return None


    def doctext(self, prefix):
        try:
            return eval(prefix+'.__doc__',self.locals, self.locals)
        except:
            return None

    def function_signature(self, function):
        try:
            f = eval(function, self.locals, self.locals)
            asp = inspect.getargspec(f)
            return asp.args, asp.defaults, asp.varargs, asp.keywords
        except:
            return None

