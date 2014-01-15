'''
Created on 28 Dec 2012

@author: huw
'''
import unittest

# Import the project root and set this to be the current working directory
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.chdir(os.path.abspath(os.path.dirname(__file__)))


from tftpud.server import readoperation
from tftpud import tftpmessages
import mocksocket


class TestServerRead(unittest.TestCase):

    def setUp(self):
        self.s = mocksocket.MockSocket()
        self.clientAddr = ('localhost', 12345)
        self.uut = None
        
    def setupRrq(self, fileName='MyFile.txt', mode='octet', options = None):
        pkt = tftpmessages.ReadRequest()
        pkt.fileName = os.path.join('data', fileName)
        pkt.mode = mode
        if options is not None:
            pkt.options = options
        
        self.uut = readoperation.ReadOperation(self.s, self.clientAddr, pkt)

    def tearDown(self):
        self.uut.abort(True)
        self.uut = None

    def testWrongFile(self):
        self.setupRrq(fileName='WrongFile')
        self.uut.join()
        
        # Check that the socket was sent 1 error packet
        self.assertEqual(self.s.countSend, 1, 'Send 1 error packet')
        dataSent1 = self.s.sentData[0][0]
        self.assertEqual(dataSent1[0], chr(0), 'opcode MSB')
        self.assertEqual(dataSent1[1], chr(tftpmessages.OPCODE_ERR), 'Error')
        self.assertEqual(dataSent1[3], chr(tftpmessages.ERR_FILE_NOT_FOUND), 'File not found')
        
        # Check that no socket reads were done
        self.assertEqual(self.s.countRecv, 0, 'recv count')
        
    def testSingleBlockTransfer(self):
        # Set up the data that will be received.
        ackPacket = tftpmessages.Acknowledgement()
        ackPacket.blockNum = 1
        rxData = [ (ackPacket.pack(), self.clientAddr) ]
        
        self.s.loadPendingRxData( rxData )
        
        self.setupRrq()
        self.uut.join()
        
        # Check that only one packet was sent, and that it was a data block.
        self.assertEqual(self.s.countSend, 1, '1 packet sent.')
        sentData = self.s.sentData[0][0]
        self.assertEqual(sentData[0], chr(0), 'opcode msb')
        self.assertEqual(sentData[1], chr(tftpmessages.OPCODE_DATA), 'opcode = Datablock')
        self.assertEqual(sentData[3], chr(1), 'block number = 1')
        
        # Check that only one rx operation was attempted
        self.assertEqual(self.s.countRecv, 1, 'Rx count')
        
    def testFourBlockTransfer(self):
        # Set up the data that will be received.
        ackPacket = tftpmessages.Acknowledgement()
        rxData = []
        for i in range(0, 4):
            ackPacket.blockNum = i + 1
            rxData.append( (ackPacket.pack(), self.clientAddr) )
        
        self.s.loadPendingRxData( rxData )
        
        self.setupRrq(fileName='MyFileMedium.txt')
        self.uut.join()
        
        # Check that 4 packets were sent; all data blocks.
        self.assertEqual(self.s.countSend, 4, '4 packet sent.')
        for i in range(0, 4):
            sentData = self.s.sentData[i][0]
            self.assertEqual(sentData[0], chr(0), 'opcode msb')
            self.assertEqual(sentData[1], chr(tftpmessages.OPCODE_DATA), 'opcode = Datablock')
            self.assertEqual(sentData[3], chr(i+1), 'block number')
        
        # Check that 4 rx operations were attempted (the 4 ack)
        self.assertEqual(self.s.countRecv, 4, 'Rx count')
    
    def testTransferFactorOfBlockSize(self):
        # Set up the data that will be received.
        ackPacket = tftpmessages.Acknowledgement()
        rxData = []
        for i in range(0, 3):
            ackPacket.blockNum = i + 1
            rxData.append( (ackPacket.pack(), self.clientAddr) )
        
        self.s.loadPendingRxData( rxData )
        
        self.setupRrq(fileName='MyFile1024.txt')
        self.uut.join()
        
        # Check that 3 packets were sent; all data blocks.
        self.assertEqual(self.s.countSend, 3, 'Expected 3 packets sent. got ' + str(self.s.countSend))
        for i in range(0, 3):
            sentData = self.s.sentData[i][0]
            self.assertEqual(sentData[0], chr(0), 'opcode msb')
            self.assertEqual(sentData[1], chr(tftpmessages.OPCODE_DATA), 'opcode = Datablock')
            self.assertEqual(sentData[3], chr(i+1), 'block number')
            
        # Check that the first data block is 512 bytes
        firstBlock = self.s.sentData[0][0]
        self.assertEqual(len(firstBlock), 512 + 4, '512 byte block')
        
        # Check that the last data block has a size of zero
        lastBlock = self.s.sentData[-1][0]
        self.assertEqual(len(lastBlock), 4, '4 byte data block (empty)')
            
    def testIncorrectSourcePort(self):
        # Set up the data that will be received.
        ackPacket = tftpmessages.Acknowledgement()
        rxData = []
        for i in range(0, 4):
            ackPacket.blockNum = i + 1
            rxData.append( (ackPacket.pack(), self.clientAddr) )
            
        # Add another ack packet in the middle with an incorrect source port.
        rxData.insert(2, (ackPacket.pack(), (self.clientAddr[0], self.clientAddr[1] + 1) ) )
        
        self.s.loadPendingRxData( rxData )
        
        self.setupRrq(fileName='MyFileMedium.txt')
        self.uut.join()
        
        # Check that 5 packets were sent; 4 data blocks + 1 error
        self.assertEqual(self.s.countSend, 5, '5 packet sent.')
        countData= 0
        countError = 0
        for sentData, toAddr in self.s.sentData:
            if sentData[1] == chr(tftpmessages.OPCODE_DATA):
                countData += 1
            elif sentData[1] == chr(tftpmessages.OPCODE_ERR):
                countError += 1
                
        self.assertEqual(countData, 4, 'data count')
        self.assertEqual(countError, 1, 'error count')
        
    def testBlockCountWrap(self):
        '''This test will use a small block size (4 bytes) in order to encourage
        the block count to wrap around.
        File size = 262143 bytes ( (0xFFFF * 4) + 3 )
        The file transfer will use the whole range of block numbers, then 
        the final block will be the wrapped around index.
        '''
        # Set up the data that will be received.
        ackPacket = tftpmessages.Acknowledgement()
        rxData = []
        
        #First ack is in response to OACK
        ackPacket.blockNum = 0
        rxData.append( (ackPacket.pack(), self.clientAddr) )
        
        # More acks for data blocks
        for i in range(0, 0xffff):
            ackPacket.blockNum = (i + 1)
            rxData.append( (ackPacket.pack(), self.clientAddr) )
            
        # Add the final wrapped packet
        ackPacket.blockNum = 1
        rxData.append( (ackPacket.pack(), self.clientAddr) )
        
        self.s.loadPendingRxData( rxData )
        
        optionsParam = {'blksize':'4'}
        self.setupRrq(fileName='MyFileLarge.txt', options=optionsParam)
        self.uut.join()
        
        # Check that 0x100001 packets were sent; one OACK, then all data blocks.
        self.assertEqual(self.s.countSend, 0x10001, '0x10001 packets sent.')
        firstPkt = self.s.sentData[0][0]
        self.assertEqual(firstPkt[0], chr(0), 'opcode msb')
        self.assertEqual(firstPkt[1], chr(tftpmessages.OPCODE_OACK), 'OACK')
        
        lastPacket = self.s.sentData[-1][0]
        self.assertEqual(lastPacket[0], chr(0), 'opcode msb')
        self.assertEqual(lastPacket[1], chr(tftpmessages.OPCODE_DATA), 'opcode = Datablock')
        self.assertEqual(lastPacket[2], chr(0), 'wrapped block number msb')
        self.assertEqual(lastPacket[3], chr(0), 'wrapped block number')
        
        # Check the packet before that as the last in the range
        lastPacket = self.s.sentData[-2][0]
        self.assertEqual(lastPacket[0], chr(0), 'opcode msb')
        self.assertEqual(lastPacket[1], chr(tftpmessages.OPCODE_DATA), 'opcode = Datablock')
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
        optionsParam = {'blksize':'51o2o'}
        self.setupRrq(fileName='MyFile.txt', options=optionsParam)
        self.uut.join()
        
        self.assertEqual(len(self.s.sentData), 1, '1 packet sent')
        pkt = self.s.sentData[0][0]
        self.assertGreaterEqual(len(pkt), 4, 'at least 4 bytes')
        self.assertEqual(pkt[1], chr(tftpmessages.OPCODE_ERR), 'Error packet')
        self.assertEqual(pkt[3], chr(tftpmessages.ERR_OPTION_FAIL), 'option failure')        
        
    def testTsizeOptions(self):
        '''
        Send a tsize = 0 option in the RRQ. Expect the OACK response to
        provide the size of the file.
        '''
        # Set up the data that will be received.
        ackPacket = tftpmessages.Acknowledgement()
        rxData = []
        
        # First ack is in response to oack
        ackPacket.blockNum = 0
        rxData.append( (ackPacket.pack(), self.clientAddr) )
        
        for i in range(0, 3):
            ackPacket.blockNum = i + 1
            rxData.append( (ackPacket.pack(), self.clientAddr) )
        
        self.s.loadPendingRxData( rxData )
        
        optionsParam = {'tsize':'0'}
        self.setupRrq(fileName='MyFile1024.txt', options=optionsParam)
        self.uut.join()
        
        # Expect an OACK containing the size.
        self.assertGreaterEqual(self.s.countSend, 1, 'at least 1 message')
        oack = self.s.sentData[0][0]
        self.assertGreaterEqual(len(oack), 2, 'oack size')
        self.assertEqual(oack[1], chr(tftpmessages.OPCODE_OACK), 'OACK opcode')
        self.assertTrue(oack.startswith('\x00\x06tsize\x001024\x00'), 'oack buffer')
        
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
