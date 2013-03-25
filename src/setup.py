#!/usr/bin/env python

from distutils.core import setup

setup(name='tftpud',
      version='0.1',
      description='A TFTP server implemented in pure python.',
      author='Huw Lewis',
      author_email='huw.lewis2409@gmail.com',
      packages=['tftpud', 'tftpud.server'],
      scripts=['tftpudServer'],
      license='MIT License')
