from time import time
from multiprocessing.process import Process
from utils import rpc, signal, _insert_sorted
from eventloop import ThreadedEventLoop

import logging
from debug import msg
logger = logging.getLogger(__name__)


class local_proxy(object):
    def _create_method(self, name):
        def method(*args, **kwargs):
            return self._dispatch_method(name, *args, **kwargs)
        return method

    def __init__(self, pipe, object_class, factory, id, _event_loop=None):
        self.factory = factory
        self.factory_id = id
        self.pipe = pipe
        self.object_class = object_class
        signal_names = [name for name in dir(self.object_class) if
                        name in self.object_class.__dict__ and
                        type(self.object_class.__dict__[name]) == signal]
        instance_method_type = type(self.__init__)
        function_tp = type(lambda x: x)
        method_names = [name for name in dir(self.object_class) if
                        name in self.object_class.__dict__ and
                        type(self.object_class.__dict__[name]) == function_tp]
        for name in signal_names:
            self.__setattr__(name, signal())
        for name in method_names:
            if name.startswith("_"):
                continue
            self.__setattr__(name, self._create_method(name))
            self.__setattr__(name + '_result', signal())
        if '_event_loop' is None:
            self.event_loop = ThreadedEventLoop()
        else:
            self.event_loop = _event_loop

        self.event_loop.register_hook(self.event_loop_hook)

    def _dispatch_method(self, method_name, *args, **kwargs):
        if '_priority' in kwargs:
            p = kwargs['_priority']
            del kwargs['_priority']
        else:
            p = rpc.PRIORITY_NORMAL
        if '_async' in kwargs:
            async = kwargs['_async']
            del kwargs['_async']
        else:
            async = True
        if '_timeout' in kwargs:
            timeout = kwargs['_timeout']
            del kwargs['_timeout']
            async = False
            if '_default' in kwargs:
                default_ret = kwargs['_default']
                del kwargs['_default']
            else:
                default_ret = None
        else:
            timeout = None
        logger.debug(msg("Timeout == ", timeout))
        command = rpc(method_name, *args, **kwargs)
        command.priority = p
        logger.debug(msg("Dispatching rpc for ", method_name))
        self.pipe.send(command)
        time_start = time()
        if timeout is not None:
            logger.debug(msg("Time start == ", time_start))
        while not async:
            ret = self._process_command(block=False, return_response_to=command.message_id)
            if ret is not None:
                return ret
            if timeout is not None and time() - time_start > timeout:
                return default_ret
            if time() % 10 == 0:
                logger.debug(self, "Time:", time())

    def _process_command(self, block=False, return_response_to=None):
        if not block and not self.pipe.poll():
            return
        try:
            command = self.pipe.recv()
        except Exception, e:
            logger.error(msg("Error when receiving command:", e))
            logger.debug(msg("Error when receiving command:", e))
            return None
        if command.rpc_type == rpc.OBJECT_MESSAGE:
            signal = self.__getattribute__(command.message_name)
            signal.emit(*command.args, **command.kwargs)
        elif command.rpc_type == rpc.OBJECT_MESSAGE_RESPONSE:
            if return_response_to == command.response_to:
                return command.response_data
            else:
                signal = self.__getattribute__(command.message_name + '_result')
                signal.emit(command.response_data)
        elif command.rpc_type == rpc.ERROR_MESSAGE:
            if return_response_to == command.response_to:
                if command.error_typ == 'exception':
                    raise command.exception
                else:
                    raise Exception("Error in remote call: " + command.error_description)

    def event_loop_hook(self):
        self._process_command(block=False)

    def terminate(self):
        self.event_loop.unregister_hook(self.event_loop_hook)
        self.factory._terminate_object(self.factory_id)

    def __del__(self):
        self.terminate()


class remote_object(Process):
    def __init__(self, pipe, object_class, *args, **kwargs):
        Process.__init__(self)
        self.object_class = object_class
        self.init_args = args
        self.init_kwargs = kwargs
        self.pipe = pipe
        self.command_queue = []
        self.message_priorities = {}

    def _connect_all(self):
        signals = [(name, self.object.__getattribute__(name)) for name in dir(self.object) if type(self.object.__getattribute__(name)) == signal]
        for (name, sign) in signals:
            sign.connect_named(name, self._signal_handler)

    def _signal_handler(self, signal_name, *args, **kwargs):
        command = rpc(signal_name, *args, **kwargs)
        self.pipe.send(command)

    def _get_method(self, method_name):
        return self.object.__getattribute__(method_name)

    def _process(self, min_priority_level=None):
        if len(self.command_queue) == 0:
            return
        else:
            command, p = self.command_queue.pop(0)
        if min_priority_level is None or self._compute_priority(command) >= min_priority_level:
            logger.debug(msg("Processing command ", command.message_name, " priority = ", command.priority))
            if command.rpc_type == rpc.OBJECT_MESSAGE:
                method = self._get_method(command.message_name)
                call_id = command.message_id
                try:
                    ret = method(*command.args, **command.kwargs)
                    response = rpc(command.message_name, ret, response_to=call_id, rpc_type=rpc.OBJECT_MESSAGE_RESPONSE)
                    self.pipe.send(response)
                except Exception, e:
                    logger.warn(msg("Exception while running command ", command.message_name, " exception == ", e))
                    response = rpc('error', response_to=call_id, rpc_type=rpc.ERROR_MESSAGE)
                    response.error_typ = 'exception'
                    try:
                        response.error_description = str(e)
                    except:
                        pass
                    response.exception = e
                    self.pipe.send(response)
        else:
            _insert_sorted(self.command_queue, command, command.priority)

    def _recv_command(self, block=False):
        if not block and not self.pipe.poll():
            return
        try:
            command = self.pipe.recv()
            logger.debug(msg("Got command ", command.message_name, " priority = ", command.priority))
            _insert_sorted(self.command_queue, command, self._compute_priority(command))
        except Exception, e:
            logger.error(msg("Error when receiving command:", e))
            logger.debug(msg("Error when receiving command:", e))

    def _single_step(self, block=False, min_priority_level=None):
        self._recv_command(block=block)
        self._process(min_priority_level=min_priority_level)

    def _proc_interrupts(self):
        self._single_step(block=False, min_priority_level=rpc.PRIORITY_INTERRUPT)

    def _wait(self):
        logger.debug("Waiting for command ...")
        self._single_step(block=True)

    def _compute_priority(self, command):
        if '_message_priority' in dir(self.object) and command.rpc_type == rpc.OBJECT_MESSAGE:
            return max(command.priority, self.object._message_priority(command.message_name))
        else:
            return command.priority

    def run(self):
        self.object = self.object_class(*self.init_args, **self.init_kwargs)
        self.object.__process_interrupts = self._proc_interrupts
        self.object._wait = self._wait
        self.object.isolated_init()
        self._connect_all()
        self.event_loop = ThreadedEventLoop()
        self.event_loop.register_hook(self._single_step)
        self.event_loop.start()
        while True:
            logger.debug(msg("remote_object.run: waiting for command ..."))
            self._single_step(block=True)
