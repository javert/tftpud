'''
Created on 25 Jan 2013

@author: huw
'''

from .. import tftpoperation
from tftpud import tftpmessages

class ReadOperation(tftpoperation.TftpOperation):
    '''
    classdocs
    '''


    def __init__(self, sock, config, fileName):
        '''
        Constructor
        '''
        self.s = sock
        self.config = config
        self.fileName = fileName
    
    def runImpl(self):
        '''the thread func'''
        
        # Send the RRQ
        rrq = tftpmessages.ReadRequest()
        rrq.fileName = self.fileName
        
        if self.config.tsize: # RFC 2349
            rrq.options['tsize'] = '0'
        if not self.config.timeout is None: # RFC 2349
            rrq.options['timeout'] = str(self.config.timeout)
        if self.config.blksize != 512: # the protocol default block size
            rrq.options['blksize'] = str(self.config.blksize)
        