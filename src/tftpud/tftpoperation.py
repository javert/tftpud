'''
Created on 26 Dec 2012

@author: huw
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
        
    def addLogMsg(self, msg):
        self.log.append(str(datetime.now()) + ': ' + msg)
        
    def processLogMessages(self, logFunc):
        for msg in self.log:
            logFunc(msg)
        self.log = []
        
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
        