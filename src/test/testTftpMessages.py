'''
Created on 26 Dec 2012

@author: huw
'''
import unittest

# Import the project root and set this to be the current working directory
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.chdir(os.path.abspath(os.path.dirname(__file__)))

from tftpud import tftpmessages

class TestRrq(unittest.TestCase):
    
    def testRxRrq(self):
        '''
        Test reception of a normal RRQ
        '''
        d = '\x00\x01SomeFile\x00netascii\x00'
        pkt = tftpmessages.create_tftp_packet_from_data(d)
        self.assertIsNotNone(pkt, 'TFTP packet is None')
        self.assertEqual(pkt.opcode, tftpmessages.OPCODE_RRQ, 'TFTP opcode is not RRQ')
        self.assertEqual(pkt.fileName, 'SomeFile', 'RRQ File Name fail')
        self.assertEqual(pkt.mode, 'netascii', 'RRQ mode fail')
        
    def testRxRrqWithoutTrailingNull(self):
        '''Test the rx of a buffer without the trailing null character. The
        test should barf as it is not a valid TFTP packet.'''
        d = '\x00\x01SomeFile\x00netascii'
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def testRxRrqWithoutMode(self):
        d = '\x00\x01SomeFile\x00'
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def testRxRrqWithoutMode2(self):
        d = '\x00\x01SomeFile'
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def testRxRrqWithoutFileName(self):
        d = '\x00\x01'
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def testRxOneBytePacket(self):
        d = '\x01'
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def testRxEmptyPacket(self):
        d = ''
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def testRxRrqWithBlkSizeExt(self):
        d = '\x00\x01SomeFile\x00netascii\x00blksize\x00513\x00'
        pkt = tftpmessages.create_tftp_packet_from_data(d)
        self.assertIsNotNone(pkt, 'TFTP packet is None')
        self.assertEqual(pkt.opcode, tftpmessages.OPCODE_RRQ, 'TFTP opcode is not RRQ')
        self.assertEqual(pkt.fileName, 'SomeFile', 'RRQ File Name fail')
        self.assertEqual(pkt.mode, 'netascii', 'RRQ mode fail')
        self.assertTrue(pkt.options.has_key('blksize'), "RRQ doesn't contain blksize option")
        self.assertEqual(pkt.options['blksize'], '513', "RRQ blksize value")
        
    def testRxRrqWithBlkSizeExt2(self):
        d = '\x00\x01SomeFile\x00netascii\x00someOption\x00someVal\x00blksize\x00513\x00'
        pkt = tftpmessages.create_tftp_packet_from_data(d)
        self.assertIsNotNone(pkt, 'TFTP packet is None')
        self.assertEqual(pkt.opcode, tftpmessages.OPCODE_RRQ, 'TFTP opcode is not RRQ')
        self.assertEqual(pkt.fileName, 'SomeFile', 'RRQ File Name fail')
        self.assertEqual(pkt.mode, 'netascii', 'RRQ mode fail')
        self.assertTrue(pkt.options.has_key('blksize'), "RRQ doesn't contain blksize option")
        self.assertEqual(pkt.options['blksize'], '513', "RRQ blksize value")
        
    def testTx(self):
        pkt = tftpmessages.ReadRequest()
        pkt.fileName = 'MyFile.txt'
        pkt.mode = 'octet'
        pkt.options['blksize'] = '1024'
        data = pkt.pack()
        self.assertEqual(data[0], chr(0), 'MSB')
        self.assertEqual(data[1], chr(1), 'opcode lsb')
        self.assertEqual(data[-1], chr(0), 'trailing null')
        data = data[2:-1]
        stringValues = data.split(chr(0))
        self.assertSequenceEqual(stringValues, ('MyFile.txt', 'octet', 'blksize', '1024'), 'RRQ string fields')
        
class TestWrq(unittest.TestCase):
    def testRxWrq(self):
        '''
        Test reception of a normal RRQ
        '''
        d = '\x00\x02SomeFile\x00netascii\x00'
        pkt = tftpmessages.create_tftp_packet_from_data(d)
        self.assertIsNotNone(pkt, 'TFTP packet is None')
        self.assertEqual(pkt.opcode, tftpmessages.OPCODE_WRQ, 'TFTP opcode is not WRQ')
        self.assertEqual(pkt.fileName, 'SomeFile', 'RRQ File Name fail')
        self.assertEqual(pkt.mode, 'netascii', 'RRQ mode fail')
        
    def testRxWrqWithoutTrailingNull(self):
        '''Test the rx of a buffer without the trailing null character. The
        test should barf as it is not a valid TFTP packet.'''
        d = '\x00\x02SomeFile\x00netascii'
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def testRxWrqWithoutMode(self):
        d = '\x00\x02SomeFile\x00'
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def testRxWrqWithoutMode2(self):
        d = '\x00\x02SomeFile'
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def testRxWrqWithoutFileName(self):
        d = '\x00\x02'
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def testRxOneBytePacket(self):
        d = '\x02'
        self.assertRaises(Exception, tftpmessages.create_tftp_packet_from_data, d)
        
    def textTx(self):
        pkt = tftpmessages.WriteRequest()
        pkt.fileName = 'MyFile.odt'
        pkt.mode = 'netascii'
        pkt.options['blksize'] = '1234'
        pkt.options['madeUp'] = 'fiction'
        data = pkt.pack()
        self.assertEqual(data[0], chr(0), 'MSB')
        self.assertEqual(data[1], chr(2), 'opcode lsb')
        self.assertEqual(data[-1], chr(0), 'trailing null')
        stringValues = data[2:-1].split(chr(0))
        self.assertSequenceEqual(stringValues, ('MyFile.odt', 'netascii', 'blksize', '1234', 'madeUp', 'fiction'), 'string values')

class TestDataBlock(unittest.TestCase):
    def testUnpack(self):
        data = '\x00\x03\xab\xcd1234567890'
        pkt = tftpmessages.create_tftp_packet_from_data(data)
        self.assertEqual(pkt.opcode, tftpmessages.OPCODE_DATA, 'Data type')
        self.assertEqual(pkt.blockNum, 0xabcd, 'block number')
        self.assertEqual(pkt.dataBlock, '1234567890', 'data block')
        
    def testPack(self):
        pkt = tftpmessages.DataBlock()
        pkt.blockNum = 255
        pkt.dataBlock = 'I am a data block.'
        data = pkt.pack()
        self.assertEqual(data[1], chr(3), 'opcode')
        
    def testPackEmpty(self):
        pkt = tftpmessages.DataBlock()
        pkt.blockNum = 0x0102
        data = pkt.pack()
        self.assertEqual(data[1], chr(tftpmessages.OPCODE_DATA), 'opcode')
        self.assertEqual(data[2], chr(1), 'block num MSB')
        self.assertEqual(data[3], chr(2), 'block num LSB')
        self.assertEqual(len(data), 4, 'empty block')
                
    def testUnpackEmpty(self):
        data  = '\x00\x03\xab\xcd'
        pkt = tftpmessages.create_tftp_packet_from_data(data)
        self.assertEqual(pkt.opcode, tftpmessages.OPCODE_DATA, 'Data type')
        self.assertEqual(pkt.blockNum, 0xabcd, 'block number')
        self.assertEqual(len(pkt.dataBlock), 0, 'empty data block')
        
class TestOack(unittest.TestCase):
    
    def testUnpack(self):
        data = '\x00\x06blksize\x001024\x00'
        pkt = tftpmessages.create_tftp_packet_from_data(data)
        self.assertEqual(pkt.opcode, tftpmessages.OPCODE_OACK, 'OACK')
        self.assertTrue(pkt.options.has_key('blksize'), 'blksize')
        self.assertEqual(pkt.options['blksize'], '1024')
        
    def testPack(self):
        oack = tftpmessages.OptionAcknowledgement()
        oack.options['myOption'] = 'myValue'
        data = oack.pack()
        self.assertEqual(data[1], chr(tftpmessages.OPCODE_OACK), 'OACK')
        expectedData = '\x00\x06myOption\x00myValue\x00'
        self.assertEqual(data, expectedData, 'packed data')
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()