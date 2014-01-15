#!/usr/bin/env python

from distutils.core import setup

setup(name='tftpud',
      version='1.0',
      description='A TFTP library implemented in pure Python. Also includes a command line server: tftpudServer.',
      author='Huw Lewis',
      author_email='huw.lewis2409@gmail.com',
      packages=['tftpud', 'tftpud.server'],
      scripts=['tftpudServer'],
      license='MIT License')
