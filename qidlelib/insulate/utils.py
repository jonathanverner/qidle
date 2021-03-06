import logging
from debug import msg
logger = logging.getLogger(__name__)

def _insert_sorted( sorted_list, element, sort_key ):
    sorted_list.append((element,sort_key))
    pos = len(sorted_list)-1
    while pos > 0 and sorted_list[pos-1][1] < sorted_list[pos][1]:
        sorted_list[pos-1],sorted_list[pos] = sorted_list[pos],sorted_list[pos-1]

class rpc(object):
    OBJECT_MESSAGE = 0
    OBJECT_MESSAGE_RESPONSE = 1
    ERROR_MESSAGE = 2

    PRIORITY_LOW = -1
    PRIORITY_NORMAL = 0
    PRIORITY_IMPORTANT = 1
    PRIORITY_INTERRUPT = 10

    NEXT_MESSAGE_ID = 0

    def __init__(self, msg = None, *args, **kwargs):
        if 'rpc_type' in kwargs:
            self.rpc_type = kwargs['rpc_type']
            del kwargs['rpc_type']
        else:
            self.rpc_type = rpc.OBJECT_MESSAGE
        self.priority = rpc.PRIORITY_NORMAL
        self.message_name = msg
        self.args = args
        self.kwargs = kwargs
        self.message_id = rpc.NEXT_MESSAGE_ID
        rpc.NEXT_MESSAGE_ID += 1
        assert type(self.message_name) == str, "Message name must be a string"
        if 'response_to' in kwargs:
            self.response_to = kwargs['response_to']
        if self.rpc_type == rpc.OBJECT_MESSAGE_RESPONSE:
            if 'response_data' in kwargs:
                self.response_data = kwargs['response_data']
            elif len(args) > 0:
                self.response_data = args[0]
            else:
                self.response_data = None
            if 'response_to' not in kwargs:
                logger.warn("RPC RESPONSE OBJECT WITH NO RESPONSE TO FIELD")
                self.response_to = -1

    def __str__(self):
        return "Type:" + str(self.rpc_type) + "; Priority:" + str(self.priority) + "; Name:" + str(self.message_name)+";"


def disconnect_object_signals(object):
    signals = [ object.__dict__[name] for name in object.__dict__ if type(object.__dict__[name]) == signal ]
    for s in signals:
        s.disconnect_all()


class SingleShotException(object):
    def __init__(self, e):
        self.exception = e
        self.already_raised = False

    def throw(self):
        if not self.already_raised:
            self.already_raised = True
            raise self.exception

    def cancel(self):
        self.already_raised = True

    def restart(self):
        self.already_raised = False

class signal(object):

    def __init__(self, *args, **kwargs):
        self.callbacks = []
        self.named_callbacks = []
        self.exception = None
        self.todo = []
        self.emitting = False

    def _raise_exception_on_emit(self, e):
        self.exception = e

    def connect_named(self, name, callback):
        self.todo.append(('connect_named',(name,callback)))
        if not self.emitting:
            self._process_todo()

    def connect(self, callback):
        self.todo.append(('connect',callback))
        if not self.emitting:
            self._process_todo()

    def disconnect(self,callback):
        logger.debug(msg("Disconnecting", callback))
        self.todo.append(('disconnect',callback))
        if not self.emitting:
            self._process_todo()

    def disconnect_all(self):
        logger.debug("Disconnecting all")
        self.todo.append(('disconnect_all',))
        if not self.emitting:
            self._process_todo()

    def _process_todo(self):
        while len(self.todo) > 0:
            op = self.todo.pop(0)
            if op[0] == 'disconnect_all':
                self.callbacks = []
                self.named_callbacks = []
            elif op[0] == 'disconnect':
                try:
                    self.callbacks.remove(op[1])
                except:
                    logger.debug(msg("Callback not present", op[1]))
                names = []
                for (n,c) in self.named_callbacks:
                    if c == op[1]:
                        names.append(n)
                for n in names:
                    self.named_callbacks.remove((n,c))
            elif op[0] == 'connect':
                self.callbacks.append(op[1])
            elif op[0] == 'connect_named':
                self.named_callbacks.append(op[1])


    def emit(self, *args, **kwargs):
        ret = True
        if self.exception is not None:
            e = self.exception
            self.exception = None
            if type(e) == SingleShotException:
                e.throw()
            else:
                raise e
        self.emitting = True
        for c in self.callbacks:
            if type(c) == signal:
                logger.debug(msg("Emmitting signal", c))
                c.emit(*args,**kwargs)
            else:
                try:
                    logger.debug(msg("Running slot", c))
                    c(*args, **kwargs)
                except Exception, e:
                    logger.warn(msg("Exception when emitting signal:", e))
                    ret = False
        for (name,c) in self.named_callbacks:
            try:
                c(name, *args, **kwargs)
            except Exception, e:
                logger.warn(msg("Exception when emitting signal:", e))
                ret = False
        self._process_todo()
        self.emitting = False
        return ret

    def __call__(self, *args, **kwargs):
        self.emit(*args, **kwargs)


def connect_all(obj, handler):
    signals = [ (name, obj.__getattribute__(name)) for name in dir(obj) if name in obj.__dict__ and type(obj.__dict__[name]) == signal ]
    for (name, sign) in signals:
        sign.connect_named(name, handler)


def cleanup(func):
    def decorated(self, *args, **kwargs):
        ret = func(self, *args, **kwargs )
        self._reset()
        return ret
    return decorated

class Tester(object):
    signal_1 = signal()
    signal_2 = signal()

    msg = "Message"
    name_1 = "Name 1"
    name_2 = "Name 2"

    def __init__(self):
        pass

    def _reset(self):
        self.signal_1 = signal()
        self.signal_2 = signal()
        self.nm_handler = None
        self.handl = None
        self.handl2 = None
        self.signal_1.connect(self.handler)
        self.signal_1.connect(self.signal_2)
        self.signal_2.connect_named(Tester.name_1, self.named_handler)

    def named_handler(self, name, string):
        self.nm_handler = (self, name, string)

    def handler(self,string):
        self.handl = string

    def handler2(self,string):
        self.handl2 = string

    @cleanup
    def test_basic_connection(self):
        self.signal_1.connect(self.handler)
        self.signal_1.emit(Tester.msg)
        return self.handl == Tester.msg

    @cleanup
    def test_signal_as_function(self):
        self.signal_1(Tester.msg)
        return self.handl == Tester.msg

    @cleanup
    def test_disconnect_all(self):
        self.signal_2.connect_named(Tester.name_2, self.named_handler)
        self.signal_2.disconnect_all()
        self.signal_1.disconnect_all()
        self.signal_1.emit(Test.msg)
        self.signal_2.emit(Test.msg)
        return self.nm_handler is None and self.handl is None

    @cleanup
    def test_disconnect(self):
        self.signal_1.connect(self.handler2)
        self.signal_1.disconnect(self.handler)
        self.signal_1.emit(Test.msg)
        return self.handl2 is None

    @cleanup
    def test_chains(self):
        self.signal_1.connect_named(Tester.name_2, self.signal_2)
        self.signal_1.emit(Test.msg)


