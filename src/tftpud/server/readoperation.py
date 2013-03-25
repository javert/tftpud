'''
Created on 26 Dec 2012

@author: huw
'''
import os
import socket # for timeout exception

from .. import tftpoperation
from .. import tftpmessages

class FileBlockSource:
    
    def __init__(self, fileName, blockSize):
        self.f = open(fileName, 'rb')
        self.blockSize = blockSize
        
    def __del__(self):
        if self.f:
            self.f.close()
            
    def getBlocks(self, maxNum):
        blocks = []
        while self.f and len(blocks) < maxNum:
            d = self.f.read(self.blockSize)
            if len(d) == 0:
                # end of file
                self.f.close()
                self.f = None
                break # end of file
            blocks.append(d)
        return blocks
    
class ReadOperation(tftpoperation.TftpOperation):
    '''
    An Server TFTP Read Operation
    '''

    def __init__(self, sock, clientAddr, pkt, timeout=3.0, retries=3):
        '''
        Constructor
        '''
        tftpoperation.TftpOperation.__init__(self)
        self.s = sock
        self.clientAddr = clientAddr
        self.fileName = pkt.fileName
        self.mode = pkt.mode
        self.blockSize = 512 # default, can be overridden by RRQ extension
        self.retries = 3
        self.abortRequested = False
        
        # Set the socket timeout to match the given param
        self.s.settimeout(timeout)
        
        self.blocks = []
        
        self.fileSource = None
        
        # Import options
        self.readOpts = pkt.options
            
        self.start()
        
    def processOptions(self):
        '''
        If there are any options that are not supported, remove them from the
        OACK packet to show that they are not to be used.
        Send an OACK packet back to the client and wait for the ACK in response.
        '''
        if len(self.readOpts) > 0:
            oack = tftpmessages.OptionAcknowledgement()
            try:
                for name, val in self.readOpts.items():
                    lowerCaseName = name.lower()
                    if name.lower() == 'blksize': # RFC 2348
                        self.blockSize = int(val)
                        oack.options[name] = val
                    elif lowerCaseName == 'timeout': # RFC 2349
                        secs = int(val)
                        if secs >= 1 and secs <= 255:
                            self.s.settimeout(int(val))
                            oack.options[name] = val
                    elif lowerCaseName == 'tsize': # RFC 2349
                        # the value should be zero.
                        if int(val) == 0:
                            # Write the actual file size back to the client in the
                            # OACK,
                            s = os.stat(self.fileName)
                            oack.options[name] = str( s.st_size )
            except:
                # Send an error packet and bail out with an exception.
                self.sendErrorPkt(tftpmessages.ERR_OPTION_FAIL, 'Failed to process RRQ options')
                raise Exception('Failed to process RRQ options')
            else:
                if len(oack.options) > 0:
                    # Send the oack
                    self.s.sendto(oack.pack(), self.clientAddr)
                    
                    # Now wait for an ack.
                    retryCount = 0
                    while not self.abortRequested and not self.waitForAck(0):
                        if retryCount < self.retries:
                            retryCount += 1
                            # resend the oack
                            self.s.sendto(oack.pack(), self.clientAddr)
                        else:
                            # Fail
                            raise Exception('Failed to receive expected ACK packet')
                else:
                    # No options. Continue as normal (as if no options).
                    pass
        else:
            # No options. Continue as normal.
            pass

                
    def runImpl(self):
        '''
        The main thread function for the Server Read Operation.
        Split the requested file into blocks, then send each one in lock-step.
        '''
        self.addLogMsg('RRQ :' + str(self.clientAddr) + ', ' + self.fileName + ' , options : ' + str(self.readOpts))
        
        # Ensure the input packet mode string is acceptable
        if self.mode.lower() != 'octet':
            self.sendErrorPkt(tftpmessages.ERR_NOT_DEFINED, 'Only octet mode supported')
            raise Exception('Only mode octet supported')
        
        # Check the file exists
        if not os.path.isfile(self.fileName):
            # Send back an error packet
            self.sendErrorPkt(tftpmessages.ERR_FILE_NOT_FOUND, 'No such file: ' + self.fileName)
        else:
            # Check the options (including the OACK/ACK exchange if required)
            self.processOptions()
            
            # The file exists, so split it into the required blocks.
            self.fileSource = FileBlockSource(self.fileName, self.blockSize)
            self.generateBlocks()
            
            blockNum = 1
            finished = False
            finalPass = False
            lastBlockSize = 0
            while not finished:
                for block in self.blocks:
                    lastBlockSize = len(block)
                    
                    if self.abortRequested:
                        raise Exception('Operation aborted')
                    
                    retryCount = 0
                    
                    # Send the data block
                    pkt = tftpmessages.DataBlock()
                    pkt.blockNum = blockNum
                    pkt.dataBlock = block
                    blockPacket = pkt.pack()
                    self.s.sendto(blockPacket, self.clientAddr)
                    
                    while not self.abortRequested and not self.waitForAck(pkt.blockNum):
                        retryCount += 1
                        if retryCount <= self.retries:
                            # Resend the previous block
                            self.s.sendto(blockPacket, self.clientAddr)
                        else:
                            errMsg = 'Failed to get ack for block ' + str(pkt.blockNum)
                            self.sendErrorPkt(tftpmessages.ERR_NOT_DEFINED, errMsg)
                            raise Exception(errMsg)
                    
                    blockNum += 1
                    if blockNum > 0xffff:
                        blockNum = 1 # or reset to zero?
                        
                # This block group has been sent. Get the next.
                if finalPass:
                    finished = True
                else:
                    self.generateBlocks()
                    if len(self.blocks) == 0:
                        finalPass = True
                        if lastBlockSize == self.blockSize:
                            # Add the one final (empty) block to terminate the operation
                            self.blocks.append('')
                    
        self.addLogMsg('RRQ operation complete')
            
    def generateBlocks(self):
        # Get up to 200 blocks
        self.blocks = self.fileSource.getBlocks(200)
        
    def waitForAck(self, blockNum):
        '''
        Wait for the timeout (socket blocking read) for the ACK packet to the given
        data block number.
        
        Return True if the expected ACK packet is received.
        Return False if nothing was received in the permitted timeout, or if an
        incorrect source port originated some data.
        Otherwise, throw an exception to terminate this transfer.
        '''
        correctSourcePort = False
        while not correctSourcePort:
            try:
                data, fromAddr = self.s.recvfrom(64) # ack should only be 4 bytes
            except socket.timeout:
                # Nothing received within the timeout
                break
            
            sourcePort = fromAddr[1]
            correctSourcePort = sourcePort == self.clientAddr[1]
            if correctSourcePort:
                pkt = tftpmessages.create_tftp_packet_from_data(data)
                if pkt.opcode == tftpmessages.OPCODE_ACK and pkt.blockNum == blockNum:
                    return True
                elif pkt.opcode == tftpmessages.OPCODE_ERR:
                    # Error received.
                    raise Exception('Error packet receive from client: ' + pkt.errorMsg)
                else:
                    # This packet is incorrect. Barf!
                    raise Exception('Invalid packet received by server read operation')
            else:
                # Incorrect source port (Transfer ID). Send an error packet back to this
                # end point and continue with this transfer.
                self.sendErrorPkt(tftpmessages.ERR_UNKNOWN_TID, 'Invalid TID')

        return False
    
    def sendErrorPkt(self, errCode, errMsg):
        errPkt = tftpmessages.Error()
        errPkt.errorCode = errCode
        errPkt.errorMsg = errMsg
        self.s.sendto(errPkt.pack(), self.clientAddr)
        self.addLogMsg('RRQ ERROR: ' + errMsg)
        
    def abort(self, block = True):
        self.abortRequested = True
        if block:
            self.join()