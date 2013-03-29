from multiprocessing.process import Process
from multiprocessing import Pipe
import time

from namedpipes import Router, NamedPipe
from utils import rpc
from objects import local_proxy, remote_object
from eventloop import ThreadedEventLoop


import logging
from debug import msg
logger = logging.getLogger(__name__)


class InsulatedFactory(Process):
    def __init__(self, event_loop = ThreadedEventLoop()):
        Process.__init__(self)
        self.server_pipe, self.client_pipe = Pipe()
        self.server_router = Router(self.server_pipe)
        self.client_router = Router(self.client_pipe)
        self.srv_command_pipe = self.server_router.create()
        self.cli_command_pipe = self.client_router.create(self.srv_command_pipe.id)
        self.children = {}
        self.client_event_loop = event_loop
        self.client_event_loop.register_hook(self.client_router.eventloop_hook)
        
    def start_event_loop(self):
        self.client_event_loop.start()
        
    def stop_event_loop(self):
        self.client_event_loop.stop()
    
    def _process_children(self):
        for i in self.children.keys():
            if self.children[i]['pipe'].poll():
                response = self.children[i]['pipe'].recv()
                self.children[i]['parent_pipe'].send(response)
                logger.debug(msg("Child ", i, " sending response."))
            if self.children[i]['parent_pipe'].poll():
                req = self.children[i]['parent_pipe'].recv()
                self.children[i]['pipe'].send(req)
                logger.debug(msg("Child ", i, " receiving request."))
    
    def run(self):
        logger.debug(msg("running."))
        while True:
            self._process_children()
            if self.srv_command_pipe.poll():
                req = self.srv_command_pipe.recv()
                logger.debug(msg("incoming data on command pipe ", req))
                if req.message_name == 'create_object':
                    try:
                        obj_id = self._create_object(req.object_class, *req.args, **req.kwargs)
                        response = rpc('created_object')
                        response.object_id = obj_id
                    except Exception, e:
                        logger.warn(msg("Object could not be created, exception thrown: ", e))
                        response = rpc('created_object')
                        response.object_id = None
                        response.exception = e
                    self.srv_command_pipe.send(response)
                elif req.message_name == 'terminate_object':
                    self._server_terminate_object(req.object_id)
                elif req.message_name == 'terminate':
                    for obj in self.children:
                        self._server_terminate_object(obj)
                    response = rpc('terminated')
                    self.srv_command_pipe.send(response)
                
                    
                    
    def create_object(self, object_class, *args, **kwargs):
        req = rpc('create_object', *args, **kwargs)
        req.object_class = object_class
        self.cli_command_pipe.send(req)
        response = self.cli_command_pipe.recv()
        assert response.message_name == 'created_object', "new_InsulatedFactory: Unknown response " + response.message_name
        if response.object_id is None:
            raise response.exception
        else:
            object_pipe = self.client_router.create(response.object_id)
            proxy_object = local_proxy( object_pipe, object_class, self, response.object_id, _event_loop = self.client_event_loop)
            self.children[response.object_id] = {
                'object':proxy_object,
                'pipe':object_pipe
            }
            return proxy_object
    
    def destroy(self):
        logger.debug("Destroying factory ...")
        req = rpc('terminate')
        logger.debug("Sending destroy command to remote factory ...")
        self.cli_command_pipe.send(req)
        logger.debug("Waiting for remote factory to destroy itself ...")
        if self.cli_command_pipe.poll(3):
            req = self.cli_command_pipe.recv()
        logger.debug("Terminating remote factory ...")
        self.terminate()
        logger.debug("Remote factory terminated.")
        
    
    def _server_terminate_object(self, object_id):
        logger.debug(msg("Terminating object ...", object_id))
        self.children[object_id]['pipe'].close()
        self.children[object_id]['object'].terminate()
        self.children[object_id]['parent_pipe'].close()
        del self.children[object_id]
        logger.debug("Object terminated")
        
    def _terminate_object(self, object_id):
        if object_id in self.children:
            req = rpc('terminate_object')
            req.object_id = object_id
            self.cli_command_pipe.send(req)
            self.children[object_id]['pipe'].close()
            self.children[object_id]['object'] = None
            del self.children[object_id]
        
    def _create_object(self, object_class, *args, **kwargs):
        local_end, child_end = Pipe()
        parent_pipe = self.server_router.create()
        self.children[parent_pipe.id] = {
            'object':remote_object( child_end, object_class, *args, **kwargs ),
            'pipe':local_end,
            'parent_pipe':parent_pipe,
        }
        logger.debug(msg("starting object ", object_class, " communication on pipe id ", parent_pipe.id, "..."))
        res = self.children[parent_pipe.id]['object'].start()
        logger.debug(msg("started successfully, result == ", res))
        return parent_pipe.id
        
        
