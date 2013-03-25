'''
Created on 25 Jan 2013

@author: huw
'''
import socket

class ClientConfig:
    def __init__(self, hostAddress):
        self.hostAddress = hostAddress # A tuple of address, port
        self.blkSize = 512 # default 512
        self.timeout = 2 # RFC 2349 - seconds timeout before retry
        self.tsize = False # RFC 2349 - set true to enable tsize option
        
class Client:
    '''
    A TFTP client.
    '''

    def __init__(self, config):
        '''
        Constructor
        '''
        self.config = config
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def readRequest(self, fileName):
        '''Initiate a read request operation'''
        pass
    
    def writeRequest(self, fileName):
        '''Initiate a write request operation'''
        pass
        