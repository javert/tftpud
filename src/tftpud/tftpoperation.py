'''
Created on 26 Dec 2012

@author: huw

All tftpud code licensed under the MIT License: http://mit-licence.org
'''

import threading
from datetime import datetime

class TftpOperation(threading.Thread):
    '''
    An abstract base class to represent a TFTP operation within the server.
    '''

    def __init__(self):
        '''
        Constructor
        '''
        threading.Thread.__init__(self)
        self.log = []
        self.logMutex = threading.Lock()
        
    def addLogMsg(self, msg, timestamp = True, newLine = True, overwrite = False):
        if timestamp:
            msg = str(datetime.now()) + ': ' + msg
            
        with self.logMutex:
            if overwrite:
                # prepend a \r character
                self.log.append('\r' + msg)
            elif newLine or len(self.log) == 0:
                self.log.append(msg)
            else:
                self.log[-1] += msg
        
    def processLogMessages(self, logFunc):
        tmpLog = []
        with self.logMutex:
            tmpLog = self.log
            self.log = []
            
        for msg in tmpLog:
            logFunc(msg)
        
    def run(self):
        try:
            self.runImpl()
        except Exception as e:
            self.addLogMsg('Error: ' + str(e) )
            
    def runImpl(self):
        raise Exception('The runImpl method must be overridden')
        
    def abort(self, block=True):
        '''A virtual method used to abort this current operation. Must be overridden
        by the concrete class.'''
        raise Exception('Must be overridden by concrete class')
        