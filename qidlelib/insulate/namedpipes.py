import time
import logging

from debug import msg
from utils import rpc

logger = logging.getLogger(__name__)

class NamedPipe(object):
    def __init__(self, id, router):
        self.router = router
        self.id = id
    
    def send(self, data):
        self.router._send(self.id, data)
        
    def recv(self):
        return self.router._recv(self.id)
    
    def poll(self, *args):
        return self.router._poll(self.id, *args)
    
    def close(self):
        self.router._close(self.id)
        
    
class Router(object):
    
    def __init__(self, pipe):
        self.pipe = pipe
        self.queues = {}
        self.next_id = 0
        self.pipes = {}
        
    def create(self, id = None):
        if id is None:
            id = self.next_id
            self.next_id += 1
        if id in self.pipes:
            return self.pipes[id]
        else:
            self.queues[id] = []
            self.pipes[id] = NamedPipe(id,self)
            return self.pipes[id]

    def _process_incoming(self,req):
        if req.message_name == 'transport' and req.pipe_id in self.queues:
            logger.debug(msg("Router._process_incoming: processing transport on pipe ", req.pipe_id, "(data ==", req.data,")"))
            self.queues[req.pipe_id].append(req.data)
            return req.pipe_id
        elif req.message_name == 'close':
            logger.debug(msg("Router._process_incoming: closing on pipe ", req.pipe_id))
            if req.pipe_id in self.queues:
                del self.queues[req.pipe_id]
        else:
            pass
            logger.debug(msg("Router._process_incoming: unexpected message type ", req.message_name, " on pipe ", req.pipe_id))
        return None
        
    def eventloop_hook(self):
        if self.pipe.poll():
            self._process_incoming(self.pipe.recv())
        
    
    def _wait_for_id(self, pipe_id):
        recv_id = None
        while recv_id != pipe_id:
            req = self.pipe.recv()
            recv_id = self._process_incoming(req)
        return self.queues[pipe_id].pop(0)
    
    def _send(self, pipe_id, data):
        logger.debug(msg("Router._send: sending data on pipe ", pipe_id, "(data ==", data,")"))
        if pipe_id not in self.queues:
            raise Exception("I/O Error: Non-existing or closed pipe")
        req = rpc('transport')
        req.pipe_id = pipe_id
        req.data = data
        self.pipe.send(req)
    
    def _recv(self, pipe_id):
        if pipe_id not in self.queues:
            raise Exception("I/O Error: Non-existing or closed pipe")
        if len(self.queues[pipe_id]) > 0:
            return self.queues[pipe_id].pop(0)
        else:
            return self._wait_for_id(pipe_id)
        
    def _poll(self, id, *args):
        if len(args) == 0:
            if (len(self.queues[id]) > 0 or (self.pipe.poll() and self._process_incoming(self.pipe.recv()) == id)):
                return True
        elif type(args[0]) in [int, float, long]:
            remaining_time = args[0]
            while remaining_time > 0:
                start_time = time.time()
                if not self.pipe.poll(remaining_time):
                    return False
                if self._process_incoming(self.pipe.recv()) == id:
                    return True
                remaining_time -= time.time()-start_time
        else:
            while True:
                self.pipe.poll()
                if self._process_incoming(self.pipe.recv()) == id:
                    return True
    
    def _close(self, pipe_id):
        if pipe_id in self.queues:
            req = rpc('close')
            req.pipe_id = pipe_id
            self.pipe.send(req)
            del self.queues[pipe_id]
