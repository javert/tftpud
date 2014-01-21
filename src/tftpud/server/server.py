'''
Created on 16 Dec 2012

@author: huw

All tftpud code licensed under the MIT License: http://mit-licence.org
'''
import threading
import socket
import random

from .. import tftpmessages
import readoperation
import writeoperation

class ServerConfig:
    '''Configuration data for the TFTP Server.
    This information may come from a config file, a GUI or whatever.
    '''
    
    def __init__(self, hostIpAddress,
                 timeout = 6.0, retries = 3, 
                 ephemeralPortRange = (2048, 65535),
                 listeningPort = 69):
        '''
        hostIpAddress - the address of this TFTP server
        timeout - (seconds, float) the time to wait for ack or data packets from the client.
        retries - the number of retransmissions to attempt before giving up.
        ephemeralPortRange - (tuple) The port range available for allocation.
        listeningPort - the UDP port on which the TFTP server listens for requests.
        '''
        self.hostIpAddress = hostIpAddress
        self.timeout = timeout # seconds (floating point)
        self.retries = retries #
        self.ephemeralPorts = ephemeralPortRange
        self.listeningPort = listeningPort
        self.logger = None
    
class Server(object):
    '''
    A TFTP server object. This runs a thread listening for and servicing
    TFTP requests from TFTP clients.
    '''

    def __init__(self, config, runNow = True):
        '''
        Constructor
        '''
        # Configurable parameters
        self.config = config
        
        self.stopThread = False
        self.ipVer = 4
        
        # A dict of TFTP operations ongoing. Keyed by port number.
        self.ongoingOperations = {}
        
        self.serverThread = threading.Thread(target=self.runServer)
        
        if runNow:
            # Start the server thread.
            self.startServer()
            
    def startServer(self):
        '''Start the server'''
        
        # Create the socket objects. If there is problem here it will throw
        # an exception in the calling thread rather than inside the server
        # thread.
        family= socket.AF_INET
        if self.config.hostIpAddress.find(':') >= 0:
            family = socket.AF_INET6
            self.ipVer = 6
            
        self.listenerSocket = socket.socket(family, socket.SOCK_DGRAM)
        self.listenerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listenerSocket.bind((self.config.hostIpAddress, self.config.listeningPort))
        
        self.listenerSocket.settimeout(2) # 2 second timeout
        
        # Now start the thread
        self.serverThread = threading.Thread(target=self.runServer)
        self.serverThread.start()
        
    def join(self):
        while self.serverThread and self.serverThread.is_alive():
            self.serverThread.join(2) #  2 second timeout to allow signals
            
    def runServer(self):
        '''Run the server object, listening for TFTP server requests.'''
        
        while not self.stopThread:
            try:
                data, dataSrc = self.listenerSocket.recvfrom(256)
                self.processListenerData(data, dataSrc)
            except socket.timeout:
                # This timeout is expected. Continue around the loop.
                pass
            
            # Do some tidying up
            garbage = []
            for portIndex, operation in self.ongoingOperations.items():
                # process the log messages from this operation
                if self.config.logger:
                    operation.processLogMessages(self.config.logger)
                
                if not operation.is_alive():
                    garbage.append(portIndex)   
                    
            for completeIndex in garbage:
                self.ongoingOperations.pop(completeIndex)
            
        # Signal any ongoing operations to stop (abort).
        for operation in self.ongoingOperations.itervalues():
            operation.abort(True)
            
        # Close the listener socket.
        self.listenerSocket.close()
        self.listenerSocket = None
    
    def processListenerData(self, data, fromAddr):
        pkt = tftpmessages.create_tftp_packet_from_data(data)
        if not pkt is None:
            if pkt.opcode in (tftpmessages.OPCODE_RRQ, tftpmessages.OPCODE_WRQ):
                
                s = None
                if self.ipVer == 4:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                else:
                    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                ephemeralPort = self.allocateEphemeralPort(s)
                
                # Create the read operation.
                if not self.ongoingOperations.has_key(ephemeralPort):
                    # Create the appropriate type of read/write operation.
                    if pkt.opcode == tftpmessages.OPCODE_RRQ:
                        self.ongoingOperations[ephemeralPort] = \
                        readoperation.ReadOperation(s, 
                                                    fromAddr, pkt,
                                                    self.config.timeout,
                                                    self.config.retries)
                    elif pkt.opcode == tftpmessages.OPCODE_WRQ:
                        self.ongoingOperations[ephemeralPort] = \
                        writeoperation.WriteOperation(s,
                                                      fromAddr, pkt,
                                                      self.config.timeout,
                                                      self.config.retries)
                else:
                    # This shouldn't happen as the allocateEphemeralPorts
                    # checks this.
                    errPkt = tftpmessages.Error()
                    errPkt.errorCode = tftpmessages.ERR_NOT_DEFINED
                    errPkt.errorMsg = 'Unknown error: TID conflict'
                    self.listenerSocket.sendto(errPkt.pack(), fromAddr)
    
    def stopServer(self, blocking = True):
        '''Stop the server thread.'''
        self.stopThread = True
        if blocking:
            self.serverThread.join()
    
    def allocateEphemeralPort(self, s):
        maxRetries = 100
        i = 0
        while i < maxRetries:
            i += 1
            ri = random.randint(self.config.ephemeralPorts[0], self.config.ephemeralPorts[1])
            if not self.ongoingOperations.has_key(ri) and self.bindPort(s, ri):
                return ri
            
        # If the code has reached this point then a reasonably large number of
        # retries has failed to find an unused operation number.
        # Go through the whole range in sequence
        for i in range(self.config.ephemeralPorts[0], self.config.ephemeralPorts[1]):
            if not self.ongoingOperations.has_key(i) and self.bindPort(s, i):
                return i
        
        raise Exception('Failed to allocate ephemeral port number')
    
    def bindPort(self, s, port):
        '''Attempt to bind the socket to the given address and port.'''
        success = False
        try:
            s.bind((self.config.hostIpAddress, port))
            success = True
        except:
            pass
        return success
    
    def processRequests(self):
        pass