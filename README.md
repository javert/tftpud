tftpud
======

TFTP Until Dinner - that is when I'm doing the development

This is a suite of Python packages and modules that implement the TFTP protocol (RFC 1350). 
Extensions implemented:
 - RFC 2347 - Option Extension
 - RFC 2348 - Block Size Option
 - RFC 2349 - Timeout & Tsize Options

Licensed under the MIT License (see LICENSE) file.

Scripts:
tftpudServer - runs a TFTP server from the command line.
tftpudClient - run a TFTP client from the command line.

Packages:
tftpud - common
tftpud.server
tftpud.client
test - unit tests

Future development ideas:
 - QT GUI for the client
