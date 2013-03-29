from threading import Timer

import logging
from debug import msg
logger = logging.getLogger(__name__)

class ThreadedEventLoop(object):
    def __init__(self):
        self.hooks = []
        self.timer = Timer(0.01, self._run)
        self.started = False
        
    def start(self):
        logger.debug("Starting event loop")
        self.started = True
        self._activate()
        
    def stop(self):
        logger.debug("Stopping event loop")
        self.timer.cancel()
        self.started = False
        
    def register_hook(self, hook):
        logger.debug(msg("Registering hook", hook))
        self.hooks.append(hook)
        self._activate()
        
    def unregister_hook(self,hook):
        try:
            self.hooks.remove(hook)
        except:
            pass
        self._activate()
        
    def _activate(self):
        if not self.started:
            return
        if len(self.hooks) > 0:
            logger.debug("Starting timer")
            self.timer.cancel()
            self.timer = Timer(0.01, self._run)
            self.timer.start()
        else:
            self.timer.cancel()
            
    def _run(self):
        logger.debug("Running hooks")
        self.timer.cancel()
        for h in self.hooks:
            h()
        self._activate()
