'''
Created on 28 Dec 2012

@author: huw
'''
import unittest

# Import the project root and set this to be the current working directory
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.chdir(os.path.abspath(os.path.dirname(__file__)))

from tftpud.server import writeoperation
from tftpud import tftpmessages
import mocksocket

class TestServerWrite(unittest.TestCase):

    def setUp(self):
        self.s = mocksocket.MockSocket()
        self.clientAddr = ('localhost', 12345)
        self.uut = None
        
    def setupWrq(self, fileName='MyFileToWrite.txt', mode='octet', rmFile=True, options = None):
        pkt = tftpmessages.WriteRequest()
        pkt.fileName = os.path.join('data', fileName)
        pkt.mode = mode
        if options is not None:
            pkt.options = options
        
        # remove the file first to avoid the already exists error.
        if rmFile and os.path.isfile(pkt.fileName):
            os.remove(pkt.fileName)
        
        self.uut = writeoperation.WriteOperation(self.s, self.clientAddr, pkt)

    def tearDown(self):
        self.uut.abort(True)
        self.uut = None

    def testIllegalPath(self):
        self.setupWrq(fileName='../WrongFile')
        self.uut.join()
        
        # Check that the socket was sent 1 error packet
        self.assertEqual(self.s.countSend, 1, 'Send 1 error packet')
        dataSent1 = self.s.sentData[0][0]
        self.assertEqual(dataSent1[0], chr(0), 'opcode MSB')
        self.assertEqual(dataSent1[1], chr(tftpmessages.OPCODE_ERR), 'Error')
        self.assertEqual(dataSent1[3], chr(tftpmessages.ERR_ACCESS_VIOLATION), 'File access violation')
    
    def testExistingFile(self):
        self.setupWrq(fileName='MyFile.txt', rmFile=False)
        self.uut.join()
        
        # Check that the socket was sent 1 error packet
        self.assertEqual(self.s.countSend, 1, 'Send 1 error packet')
        dataSent1 = self.s.sentData[0][0]
        self.assertEqual(dataSent1[0], chr(0), 'opcode MSB')
        self.assertEqual(dataSent1[1], chr(tftpmessages.OPCODE_ERR), 'Error')
        self.assertEqual(dataSent1[3], chr(tftpmessages.ERR_FILE_ALREADY_EXISTS), 'File already exists')
        
        
    def testSingleBlockTransfer(self):
        # Set up the data that will be received.
        dataPacket = tftpmessages.DataBlock()
        dataPacket.blockNum = 1
        dataPacket.dataBlock = 'My single data block. Less than 512 bytes to terminate the transfer.'
        rxData = [ (dataPacket.pack(), self.clientAddr) ]
        
        self.s.loadPendingRxData( rxData )
        
        self.setupWrq(fileName='SingleTransfer.txt')
        self.uut.join()
        
        # Check that 2 packets were sent, both ACK.
        self.assertEqual(self.s.countSend, 2, '2 packets sent.')
        for i in range(0, 2):
            sentData = self.s.sentData[i][0]
            self.assertEqual(sentData[0], chr(0), 'opcode msb')
            self.assertEqual(sentData[1], chr(tftpmessages.OPCODE_ACK), 'opcode = Ack')
            self.assertEqual(sentData[3], chr(i), 'block number = ' + str(i))
        
        # Check that only one rx operation was attempted
        self.assertEqual(self.s.countRecv, 1, 'Rx count')
        
        self.assertTrue(os.path.isfile(
                                       os.path.join('data', 'SingleTransfer.txt')), 'file has been written')
        
    def testFourBlockTransfer(self):
        # Set up the data that will be received.
        dataPacket = tftpmessages.DataBlock()
        rxData = []
        for i in range(0, 4):
            dataPacket.blockNum = i + 1
            dataPacket.dataBlock = '12345678' * 64 # 512 bytes
            if i == 3: # truncate the block
                dataPacket.dataBlock = dataPacket.dataBlock[:-1]
            rxData.append( (dataPacket.pack(), self.clientAddr) )
                    
        self.s.loadPendingRxData( rxData )
        
        self.setupWrq(fileName='FourBlockFile.txt')
        self.uut.join()
        
        # Check that 5 packets were sent; all ack.
        self.assertEqual(self.s.countSend, 5, '5 packet sent.')
        for i in range(0, 5):
            sentData = self.s.sentData[i][0]
            self.assertEqual(sentData[0], chr(0), 'opcode msb')
            self.assertEqual(sentData[1], chr(tftpmessages.OPCODE_ACK), 'opcode = ACK')
            self.assertEqual(sentData[3], chr(i), 'block number')
        
        # Check that 4 rx operations were attempted (the 4 ack)
        self.assertEqual(self.s.countRecv, 4, 'Rx count')
        
        self.assertTrue(os.path.isfile(os.path.join('data','FourBlockFile.txt')), 'File not written')
        
    def testIncorrectSourcePort(self):
        # Set up the data that will be received.
        dataPacket = tftpmessages.DataBlock()
        dataPacket.dataBlock = '12345678' * 64 # 512 bytes
        rxData = []
        for i in range(0, 4):
            dataPacket.blockNum = i + 1
            if i == 3: # last in sequence needs a smaller (or empty) block
                dataPacket.dataBlock = ''
                
            rxData.append( (dataPacket.pack(), self.clientAddr) )
            
            
        # Add another packet in the middle with an incorrect source port.
        rxData.insert(2, (dataPacket.pack(), (self.clientAddr[0], self.clientAddr[1] + 1) ) )
        
        self.s.loadPendingRxData( rxData )
        
        self.setupWrq(fileName='incorrectSourcePort.txt')
        self.uut.join()
        
        # Check that 4 packets were sent; 5 ack + 1 error
        self.assertEqual(self.s.countSend, 6, '6 packets sent.')
        countAck = 0
        countError = 0
        for sentData, toAddr in self.s.sentData:
            if sentData[1] == chr(tftpmessages.OPCODE_ACK):
                countAck += 1
            elif sentData[1] == chr(tftpmessages.OPCODE_ERR):
                countError += 1
                
        self.assertEqual(countAck, 5, 'Ack count')
        self.assertEqual(countError, 1, 'Error count')
        
    def testBlockCountWrap(self):
        '''This test will use a small block size (4 bytes) in order to encourage
        the block count to wrap around.
        File size = 262144 bytes ( (0xFFFF * 4) + 1 )
        The file transfer will use the whole range of block numbers, then 
        the final block will be the wrapped around index.
        '''
        # Set up the data that will be received.
        dataPacket = tftpmessages.DataBlock()
        dataPacket.blockNum
        dataPacket.dataBlock = 'abcd'
        rxData = []
        for i in range(0, 0xffff):
            dataPacket.blockNum = (i + 1)
            rxData.append( (dataPacket.pack(), self.clientAddr) )
            
        # Add the final wrapped packet
        dataPacket.blockNum = 0
        dataPacket.dataBlock = 'abc'
        rxData.append( (dataPacket.pack(), self.clientAddr) )
        
        self.s.loadPendingRxData( rxData )
        
        optionsParam = {'blksize':'4'}
        self.setupWrq(fileName='MyLargeFileToWrite.txt', options=optionsParam)
        self.uut.join()
        
        # Check that 0x10000 packets were sent; all acks.
        self.assertEqual(self.s.countSend, 0x10001, '0x10001 packets sent.')
        lastPacket = self.s.sentData[-1][0]
        self.assertEqual(lastPacket[0], chr(0), 'opcode msb')
        self.assertEqual(lastPacket[1], chr(tftpmessages.OPCODE_ACK), 'opcode = ACK')
        self.assertEqual(lastPacket[2], chr(0), 'wrapped block number msb')
        self.assertEqual(lastPacket[3], chr(0), 'wrapped block number')
        
        # Check the packet before that as the last in the range
        lastPacket = self.s.sentData[-2][0]
        self.assertEqual(lastPacket[0], chr(0), 'opcode msb')
        self.assertEqual(lastPacket[1], chr(tftpmessages.OPCODE_ACK), 'opcode = Datablock')
        self.assertEqual(lastPacket[2], chr(255), 'wrapped block number msb')
        self.assertEqual(lastPacket[3], chr(255), 'wrapped block number')
        
    def testIllegalBlockSize(self):
        '''
        This test will request a blksize option with a value that fails to
        convert into an integer.
        Expect an error packet to be sent back to the client indicating a failure
        to negotiate the option.
        '''
        # Set up the data that will be received.
        optionsParam = {'blksize':'4o'}
        self.setupWrq(fileName='ShouldNotGetWritten.txt', options=optionsParam)
        self.uut.join()
        
        self.assertEqual(len(self.s.sentData), 1, '1 packet sent')
        pkt = self.s.sentData[0][0]
        self.assertGreaterEqual(len(pkt), 4, 'at least 4 bytes')
        self.assertEqual(pkt[1], chr(tftpmessages.OPCODE_ERR), 'Error packet')
        self.assertEqual(pkt[3], chr(tftpmessages.ERR_OPTION_FAIL), 'option failure')

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()