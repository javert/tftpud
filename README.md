tftpud
======

TFTP Until Dinner - it makes no sense. Mabe I'm thinking of pudding?

This is a suite of Python packages and modules that implement the TFTP protocol (RFC 1350). 
Extensions implemented:
 - RFC 2347 - Option Extension
 - RFC 2348 - Block Size Option
 - RFC 2349 - Timeout & Tsize Options

Licensed under the MIT License (see LICENSE) file.

Scripts:
tftpudServer - runs a TFTP server from the command line.

Packages:
tftpud - common
tftpud.server
test - unit tests

Future development ideas:
 - implement netascii mode
 - complete command line client
 - QT GUI for the client
