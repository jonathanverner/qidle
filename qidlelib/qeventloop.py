from PyQt4.QtCore import QObject, QTimer, pyqtSlot

import logging
from insulate.debug import msg
logger = logging.getLogger(__name__)


class QEventLoop(QObject):
    def __init__(self):
        super(QObject, self).__init__()
        self.hooks = []
        self.waiting_for_shot = False
        self.started = False
        self.run_count = 0
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._run)

    def start(self):
        logger.debug("Starting event loop")
        self.started = True
        self._activate()

    def stop(self):
        logger.debug("Stopping event loop")
        self.timer.stop()
        self.started = False

    def register_hook(self, hook):
        logger.debug(msg("Registering hook", hook))
        self.hooks.append(hook)
        self._activate()

    def unregister_hook(self, hook):
        try:
            self.hooks.remove(hook)
        except:
            pass
        self._activate()

    def _activate(self):
        if len(self.hooks) > 0 and not self.waiting_for_shot and self.started:
            self.waiting_for_shot = True
            self.timer.start(10)
            if self.run_count % 1000 == 0:
                logger.debug(msg(
                    "Activating eventloop, timerID:", self.timer.timerId()))

    @pyqtSlot()
    def _run(self):
        if self.run_count % 1000 == 0:
            logger.debug("Running hooks")
        self.run_count += 1
        for h in self.hooks:
            h()
        self.waiting_for_shot = False
        self._activate()

    def __del__(self):
        logger.debug("Deleting event event loop")
        self.stop()
