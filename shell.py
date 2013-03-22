from multiprocessing.process import Process
from multiprocessing import Pipe

from threading import Timer
from PyQt4.QtCore import pyqtSignal, pyqtSlot, QObject, QTimer
from code import InteractiveInterpreter
from rlcompleter import Completer
from qidle.debug import debug
import sys, os



class Data(object):
    def __init__(self,command,data=None):
        self.command = command
        self.data = data

class ProxyWriter(object):
    def __init__(self,proxy, name):
        self.proxy = proxy
        self.name = name
    
    def write(self,str):
        self.proxy.writeToStream(str,self.name)
        
    def flush(self):
        pass

class remoteShell(Process):
    def __init__(self,pipe,locals=None,filename=None):
        Process.__init__(self)
        self.locals = locals
        if not self.locals:
            self.locals = {}
        self.locals['__name__']=filename
        self.completer = Completer(self.locals)
        self.pipe = pipe
        self.stderr_proxy = ProxyWriter(self,"stderr")
        self.os = os
        self.locals['__shell__'] = self
        
        
    def run(self):
        self.interpreter = InteractiveInterpreter(locals=self.locals)
        self.interpreter.write = self.writeMSG
        sys.stdin = self
        sys.stdout = self
        sys.stderr = self.stderr_proxy
        while True:
            data = self.pipe.recv()
            self._processCommand(data, masked_commands = ['write', 'interrupt'])
                
    def _processCommand(self, data, masked_commands = [], allowed_commands = []):
        if (len(allowed_commands) > 0 and data.command not in allowed_commands) or (len(masked_commands) > 0 and data.command in masked_commands):
            debug("remoteShell._processCommand: Masked command ", data.command)
            return None
        if data.command == 'execute':
            code = unicode(data.data)
            debug("remoteShell.runsource: Running code")
            debug("*"*30)
            debug(code)
            debug("*"*30)
            ret = self.interpreter.runsource(code+"\n")
            debug("remoteShell.runsource: Finished run, ret == ", ret)
            self.pipe.send(Data('finishedExecution'))
            return True
        elif data.command == 'write':
            return unicode(data.data)
        elif data.command == 'flushed':
            return True
        elif data.command == 'interrupt':
            raise KeyboardInterrupt
        elif data.command == 'complete':
            reply = Data('complete')
            reply.completions = self.completion(data.completion_prefix)
            self.pipe.send(reply)
        else:
            debug("remoteShell._processCommand: Unknown command ", data.command)
            return None
            
                
    def completion(self, prefix):
        ret = []
        i = 0
        cmpl = self.completer.complete(unicode(prefix),i)
        while cmpl is not None:
            ret.append(cmpl)
            i += 1
            cmpl = self.completer.complete(unicode(prefix),i)
            if i > 50:
                debug("remoteShell.completion: Too many completions, quitting ...")
                break
        return ret
            
        
    def writeToStream(self,str,stream_name):
        debug("remoteShell.writeToStream(",stream_name,"):",str)
        data = Data('write',str)
        data.stream = stream_name
        self.pipe.send(data)
        if self.pipe.poll():
            self._processCommand(self.pipe.recv(), allowed_commands=['interrupt'])
        
    def writeMSG(self,str):
        self.writeToStream(str,"msg")
        
    def write(self,str):
        self.writeToStream(str,"stdout")
        
    def readline(self):
        debug("remoteShell.readline")
        self.pipe.send(Data('readline'))
        data = self.pipe.recv()
        return self._processCommand(data, allowed_commands = ['write','interrupt']) or ""
    
    def flush(self):
        self.pipe.send(Data('flush'))
        while True:
            data = self.pipe.recv()
            if self._processCommand(data, allowed_commands = ['flushed','interrupt']):
                return
    def close(self):
        return
        
class ShellManager(QObject):
    
    waitingForInput = pyqtSignal()
    finished_running = pyqtSignal()
    write = pyqtSignal(unicode,unicode)
    shell_restarted = pyqtSignal()
    
    def __init__(self, remote_shell=None, pipe=None):
        super(ShellManager, self).__init__()
        if remote_shell is not None:
            self.shell = remote_shell
            self.pipe = pipe
            self.shell_running = True
        self.start_shell()
        
    @pyqtSlot()
    def quit(self):
        self.shell.terminate()
        
    def start_shell(self):
        self.pipe, child_pipe = Pipe()
        self.shell = remoteShell(child_pipe)
        self.shell.start()
        self.shell_running = True
        
    
    def killShell(self):
        self.shell_running = False
        self.shell.terminate()
        self.pipe = None
        
    def restart_shell(self):
        self.killShell()
        self.start_shell()
    
    def _processData(self, data):
        if data.command == 'write':
            try:
                self.write.emit(data.data,data.stream)
            except:
                debug("ShellManager._processData: No stream available, defaulting to stdout")
                self.write.emit(data.data,"stdout")
        elif data.command == 'readline':
            self.waitingForInput.emit()
        elif data.command == 'finishedExecution':
            debug("ShellManager._processData: finishedExecution")
            self.waiting_for_interrupt = False
            self.finished_running.emit()
            return False # Stop polling
        elif data.command == 'flush':
            self.pipe.send(Data('flushed'))
        return True # Continue polling
        
    def _poll(self):
        continue_polling = True
        try:
            if self.shell_running and self.pipe.poll():
                continue_polling = self._processData( self.pipe.recv() )
        finally:
            if continue_polling:
                QTimer.singleShot(10,self._poll)
        
    
    def get_completions(self, completion_prefix):
        data = Data('complete')
        data.completion_prefix = completion_prefix
        self.pipe.send(data)
        while True:
            data = self.pipe.recv()
            if data.command != 'complete':
                debug("ShellManager.complete: Unexpected command ", data.command, " from pipe.")
                return []
            return data.completions
        
    @pyqtSlot(unicode)
    def sendInput(self, str):
        self.pipe.send(Data('write',str))
        
    @pyqtSlot(unicode)
    def execute_code(self, code):
        self.pipe.send(Data('execute',code))
        QTimer.singleShot(0,self._poll)
        
    @pyqtSlot()
    def interrupt(self):
        debug("ShellManager.interrupt")
        self.pipe.send(Data('interrupt'))
        self.waiting_for_interrupt = True
        QTimer.singleShot(500,self._hardInterrupt)
    
    @pyqtSlot()
    def _hardInterrupt(self):
        debug("ShellManager._hardInterrupt: processing incoming events...")
        while self.pipe.poll():
            self._processData(self.pipe.recv())
        if self.waiting_for_interrupt:
            debug("ShellManager._hardInterrupt: restarting shell...")
            self.waiting_for_interrupt = False
            self.restart_shell()
            self.shell_restarted.emit()
            
    def __del__(self):
        self.quit()
