'''
Created on 31 Dec 2012

@author: huw

All tftpud code licensed under the MIT License: http://mit-licence.org
'''
import os
import socket
from .. import tftpoperation
from .. import tftpmessages

class WriteOperation(tftpoperation.TftpOperation):
    '''
    A TFTP Write operation to process a WRQ
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
        self.blockSize = 512 # default, can be overridden by WRQ extension
        self.retries = 3
        self.abortRequested = False
        self.blocksToCache = 100
        # Set the socket timeout to match the given param
        self.s.settimeout(timeout)
        
        self.blocks = []
        self.blockNum = 0
        
        # The file handle to be written
        self.f = None
        
        self.writeOptions = pkt.options
            
        self.start()
        
    def __del__(self):
        if not self.f is None:
            self.f.close()
            
    def abort(self, block=True):
        self.abortRequested = True
        if block:
            self.join()
        
    def runImpl(self):
        '''The thread function for the WRQ operation.
        Send back an ACK packet, then wait for the data packets to arrive.
        '''
        self.addLogMsg('WRQ: ' + str(self.clientAddr) + ', ' + self.fileName + ' , options : ' + str(self.writeOptions))
        
        try:
            if self.mode.lower() != 'octet':
                self.sendErrorPkt(tftpmessages.ERR_NOT_DEFINED, 'Only octet mode supported')
                raise Exception('Only octet mode supported')
            
            if not self.openFileForWriting():
                raise Exception('Invalid file name')
            
            # Handle the options given in the request.
            # This processing returns either and OACK or ACK packet to the client.
            self.processOptions()
            
            self.processDataPackets()
            
            # Close the file
            self.f.close()
            self.f = None
        except Exception, e:
            self.addLogMsg(str(e))            
        
    def openFileForWriting(self):
        '''Check that the file name is ok for writing.'''
        if self.fileName.find('..') >= 0:
            self.sendErrorPkt(tftpmessages.ERR_ACCESS_VIOLATION, 'Invalid file name')
            return False
        if os.path.isdir(self.fileName) or os.path.isfile(self.fileName):
            self.sendErrorPkt(tftpmessages.ERR_FILE_ALREADY_EXISTS,
                              'File ' + self.fileName + ' already exists')
            return False
        
        # Attempt to open the file for writing
        try:
            self.f = open(self.fileName, 'wb')
        except:
            self.sendErrorPkt(tftpmessages.ERR_ACCESS_VIOLATION,
                              'Failed to open file for writing')
            return False
        
        return True
    
    def processOptions(self):
        if len(self.writeOptions) > 0:
            oack = tftpmessages.OptionAcknowledgement()
            try:
                for name, val in self.writeOptions.items():
                    lowerCaseName = name.lower()
                    if lowerCaseName == 'blksize': # RFC 2348
                        self.blockSize = int(val)
                        oack.options[name] = val
                    elif lowerCaseName == 'timeout': # RFC 2349
                        secs = int(val)
                        if secs >= 1 and secs <= 255:
                            self.s.settimeout(int(val))
                            oack.options[name] = val
                    elif lowerCaseName == 'tsize': # RFC 2349
                        # Accept whatever size as long as it translates to an integer
                        oack.options[name] = str( int(val) )
            except:
                # Send an error packet, then bail out of the operation thread
                # via an exception
                self.sendErrorPkt(tftpmessages.ERR_OPTION_FAIL, 'Failure to process options')
                
                # Now exit
                raise Exception('Failure to process WRQ options')
            else:
                # Send either the OACK, or the plain ACK back to the client
                if len(oack.options) > 0:
                    # We have accepted at least one option. Send back the oack.
                    self.s.sendto( oack.pack(), self.clientAddr )
                else:
                    # No options accepted. Send the plain ACK packet to accept the
                    # request without options
                    self.sendAckPkt(0)
        else:
            # No options, return the ACK packet (block num = 0)
            self.sendAckPkt(0)
    
    def sendErrorPkt(self, errCode, errMsg = ''):
        errPkt = tftpmessages.Error()
        errPkt.errorCode = errCode
        errPkt.errorMsg = errMsg
        self.s.sendto(errPkt.pack(), self.clientAddr)
        
    def sendAckPkt(self, blockNum):
        ackPkt = tftpmessages.Acknowledgement()
        ackPkt.blockNum = blockNum
        self.s.sendto(ackPkt.pack(), self.clientAddr)
            
    def processDataPackets(self):
        # Wait for the next data block
        fail = False
        complete = False
        numBlocks = 0
        while not fail and not complete:
            dataPkt = self.waitForData()
            if dataPkt is not None:
                # Check that this is the next sequential block number
                blockNum = dataPkt.blockNum
                if ( blockNum == (self.blockNum + 1) or
                     (self.blockNum == 0xffff and blockNum in (0, 1)) ):
                    self.blockNum = dataPkt.blockNum
                    self.blocks.append(dataPkt.dataBlock)
                    self.sendAckPkt(self.blockNum)
                    numBlocks += 1
                    
                    if len(dataPkt.dataBlock) < self.blockSize:
                        complete = True
                        
                    # Write the blocks to the file
                    if complete or len(self.blocks) > self.blocksToCache:
                        self.f.writelines(self.blocks)
                        self.blocks = []
                else:
                    # invalid block number. Abort
                    errMsg = 'Incorrect block number ' + str(blockNum)
                    self.sendErrorPkt(tftpmessages.ERR_NOT_DEFINED, errMsg)
                    raise Exception(errMsg)
            else:
                # No data packet received in timeout (and retries).
                fail = True
                
        if complete:
            self.addLogMsg('WRQ operation complete in %d blocks' % numBlocks)
        else:
            self.addLogMsg('WRQ operation failed')
            
    def waitForData(self):
        '''Wait for a data packet to be received, and return it.
        If a packet with an incorrect TID is received, send an error and continue.
        If nothing is received within the timeout, re-send the last ack packet
        and continue to wait...
        '''
        pkt = None
        count = 0
        while not pkt:
            data = None
            fromAddr = None
            try:
                data, fromAddr = self.s.recvfrom(self.blockSize + 256)
            except socket.timeout:
                # Timeout. try again.
                count += 1
                if count >= self.retries:
                    # Give up
                    break
                else:
                    # Resend the last ack packet
                    self.sendAckPkt(self.blockNum)
                    
            incorrectSourcePort = ( fromAddr is not None and
                                  fromAddr[1] != self.clientAddr[1])
            if incorrectSourcePort:
                # Incorrect source port (Transfer ID). Send an error packet back to this
                # end point and continue with this transfer.
                self.sendErrorPkt(tftpmessages.ERR_UNKNOWN_TID,'Invalid TID')
            elif data is not None:
#                # Parse into a packet
                try:
                    pkt = tftpmessages.create_tftp_packet_from_data(data)
                except:
                    # Failed to parse data
                    self.sendErrorPkt(tftpmessages.ERR_NOT_DEFINED,
                                      'Failed to parse packet from client')
                    raise Exception('Failed to parse packet from client')
        
        if pkt is not None:
            if pkt.opcode == tftpmessages.OPCODE_DATA:
                # Return this packet to the calling method
                return pkt
            elif pkt.opcode == tftpmessages.OPCODE_ERR:
                # The client has barfed.
                raise Exception('ERROR received from client: '
                                + tftpmessages.errCodeToString(pkt.errorCode)
                                + ' '  + pkt.errorMsg)
            else:
                raise Exception('Unexpected opcode ' + str(pkt.opcode))
        return None
    