'''
Created on 28 Dec 2012

@author: huw
'''
import socket
import time


class MockSocket:
    
    def __init__(self):
        self.countRecv = 0
        self.countSend = 0
        self.sentData = []
        self.pendingRxData = [] # (data, fromAddr)
        
    def loadPendingRxData(self, dataToRx):
        self.pendingRxData = dataToRx
    
    def sendto(self, data, address):
        self.sentData.append((data, address))
        self.countSend += 1
    
    def recvfrom(self, length):
        '''Receive stuff.'''
        self.countRecv += 1
        if len(self.pendingRxData) > 0:
            data =  self.pendingRxData.pop(0)
            return data[0], data[1]
        else:
            # Nothing to return, so pretend to have to timeout
            time.sleep(1)
            raise socket.timeout()
    
    def setsockopt(self, level, opt, val):
        pass
    
    def settimeout(self, val):
        pass