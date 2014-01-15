'''
Created on 26 Dec 2012

@author: huw

All tftpud code licensed under the MIT License: http://mit-licence.org
'''
import struct

# Opcode contants
OPCODE_RRQ = 1
OPCODE_WRQ = 2
OPCODE_DATA = 3
OPCODE_ACK = 4
OPCODE_ERR = 5
OPCODE_OACK = 6 # RFC2347 - Option Ack

# Error constants
ERR_NOT_DEFINED = 0
ERR_FILE_NOT_FOUND = 1
ERR_ACCESS_VIOLATION = 2
ERR_DISK_FULL = 3
ERR_ILLEGAL_TFTP_OPERATION = 4
ERR_UNKNOWN_TID = 5
ERR_FILE_ALREADY_EXISTS = 6
ERR_NO_SUCH_USER = 7
ERR_OPTION_FAIL = 8  # RFC23347 - Option Ack

def get_opcode(data):
    '''Extract the opcode from the data buffer'''
    s = struct.unpack_from('>H', data)
    return s[0]

def create_tftp_packet_from_data(data):
    '''Create a TFTP packet object from the data.
    Throws an exception if the parsing fails e.g. run out of expected data.'''
    opcode = get_opcode(data)
    pkt = None
    if opcode == OPCODE_RRQ:
        pkt = ReadRequest()
    elif opcode == OPCODE_WRQ:
        pkt = WriteRequest()
    elif opcode == OPCODE_DATA:
        pkt = DataBlock()
    elif opcode == OPCODE_ACK:
        pkt = Acknowledgement()
    elif opcode == OPCODE_ERR:
        pkt = Error()
    elif opcode == OPCODE_OACK:
        pkt = OptionAcknowledgement()
        
    if not pkt is None:
        pkt.receive(data[2:])
        return pkt
    else:
        raise Exception('Unknown opcode ' + str(opcode))
    
        
def errCodeToString(err):
    lookup = { ERR_ACCESS_VIOLATION : 'ERR_ACCESS_VIOLATION',
              ERR_DISK_FULL : 'ERR_DISK_FULL',
              ERR_FILE_ALREADY_EXISTS : 'ERR_FILE_ALREADY_EXISTS',
              ERR_FILE_NOT_FOUND : 'ERR_FILE_NOT_FOUND',
              ERR_ILLEGAL_TFTP_OPERATION : 'ERR_ILLEGAL_TFTP_OPERATION',
              ERR_NO_SUCH_USER : 'ERR_NO_SUCH_USER',
              ERR_NOT_DEFINED : 'ERR_NOT_DEFINED',
              ERR_UNKNOWN_TID : 'ERR_UNKNOWN_TID'}
    if lookup.has_key(err):
        return lookup.get(err)
    else:
        return 'Unknown error code ' + str(err)
    
class TftpPacket:
    def __init__(self, opcode):
        self.opcode = opcode
        
    def receive(self, data):
        pass
    def pack(self):
        pass

class ReadRequest(TftpPacket):
    def __init__(self):
        TftpPacket.__init__(self, OPCODE_RRQ)
        self.fileName = ''
        self.mode = ''
        self.options = {}
        
    def receive(self, data):        
        # The final byte must be a NULL
        if data[-1] != '\x00':
            raise Exception('Missing final null character')
        
        # Extract the filename and mode string
        params = data.split('\x00')
        self.fileName = params[0]
        self.mode = params[1]
        
        if len(self.fileName)  == 0:
            raise Exception('Failed to receive fileName')
        if len(self.mode) == 0:
            raise Exception('Failed to receive mode')
        
        if len(params) >= 2:
            params = params[2:]
            while len(params) >= 2:
                self.options[params[0]] = params[1]
                params = params[2:]
                
    def pack(self):
        null = '\x00'
        data = struct.pack('>H', self.opcode)
        data += self.fileName + null + self.mode + null
        for option in self.options.iteritems():
            data += option[0] + null + option[1] + null
        return data
        
class WriteRequest(TftpPacket):
    def __init__(self):
        TftpPacket.__init__(self, OPCODE_WRQ)
        self.fileName = ''
        self.mode = ''
        self.options = {}
        
    def receive(self, data):
        # The final byte must be a NULL
        if data[-1] != '\x00':
            raise Exception('Missing final null character')
          
        # Extract the filename and mode string
        params = data.split('\x00')
        self.fileName = params[0]
        self.mode = params[1]
        
        if len(self.fileName)  == 0:
            raise Exception('Failed to receive fileName')
        if len(self.mode) == 0:
            raise Exception('Failed to receive mode')
        
        if len(params) > 2:
            params = params[2:]
            while len(params) > 2:
                self.options[params[0]] = params[1]
                params = params[2:]
                
    def pack(self):
        null = '\x00'
        data = struct.pack('>H', self.opcode)
        data += self.fileName + null + self.mode + null
        for option in self.options.iteritems():
            data += option[0] + null + option[1] + null
        return data
        
class DataBlock(TftpPacket):
    def __init__(self):
        TftpPacket.__init__(self, OPCODE_DATA)
        self.blockNum = 0
        self.dataBlock = ''
        
    def receive(self, data):        
        # Extract the data block
        self.blockNum = struct.unpack_from('>H', data)[0]
        self.dataBlock = data[2:]
        
    def pack(self):
        data = struct.pack('>HH', self.opcode, self.blockNum)
        data += self.dataBlock
        return data
    
class Acknowledgement(TftpPacket):
    def __init__(self):
        TftpPacket.__init__(self, OPCODE_ACK)
        self.blockNum = 0
        
    def receive(self, data):        
        self.blockNum = struct.unpack_from('>H', data)[0]
        
    def pack(self):
        data = struct.pack('>HH', self.opcode, self.blockNum)
        return data
        
class Error(TftpPacket):
    def __init__(self):
        TftpPacket.__init__(self, OPCODE_ERR)
        self.errorCode = 0
        self.errorMsg = ''
        
    def receive(self, data):
        self.errorCode = struct.unpack_from('>H', data)[0]
        self.errorMsg = data[2:]
        
    def pack(self):
        data = struct.pack('>HH', self.opcode, self.errorCode)
        data += self.errorMsg + '\x00'
        return data
    
class OptionAcknowledgement(TftpPacket):
    '''This is defined by RFC2347 for the negotiation of RRQ and WRQ options.'''
    def __init__(self):
        TftpPacket.__init__(self, OPCODE_OACK)
        self.options = {}
        
    def receive(self, data):
        # The final byte must be null terminated.
        null = chr(0)
        if data[-1] != null:
            raise Exception('OACK not null terminated')
        
        # This is a sequence of null terminated strings.
        items = data.strip(null).split(null)
        options= {}
        while len(items) > 1:
            name = items.pop(0)
            val = items.pop(0)
            options[name] = val
            
        if len(items) > 0:
            raise Exception('OACK contained an odd number of null terminated strings')
        
        if len(options) == 0:
            raise Exception('Empty options list in OACK')
        self.options = options
        
    def pack(self):
        if len(self.options) == 0:
            raise Exception('Empty options list')
        data = struct.pack('>H', self.opcode)
        null = '\x00'
        for opt in self.options.items():
            data += null.join(opt) + null
        return data