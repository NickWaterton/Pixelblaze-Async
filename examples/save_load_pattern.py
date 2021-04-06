#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 save_load_pattern.py
 
Pixelblaze based LED controller for APA102/SK9822 LED Strips
Working Example using PixelblazeClient
 
 MQTT interface for pixelblaze v3
 N Waterton V 1.0 16th March 2021: Initial release
 N Waterton V1.0.1 6th April 20201; added valid_ip
'''

import sys
import logging
import asyncio
import argparse

try:
    from pixelblaze_async.PixelblazeClient import PixelblazeClient
except (ImportError, ModuleNotFoundError):
    from PixelblazeClient import PixelblazeClient
    

__version__ = "1.0.1"

class PixelblazePattern(PixelblazeClient):
    '''
    Save patterns as both .epe file and .bin file
    or
    Load binarys pattern from .bin file
    '''
    
    __version__ = "1.0.0"

    def __init__(self, pixelblaze_ip=None):           
        super().__init__(pixelblaze_ip)
                         
    async def save_pattern(self, patterns=[]):
        await self.start_ws()
        for pattern in patterns:
            self.log.info('Saving {}'.format(pattern))
            if await self.save_binary_file(pattern, True):
                await self.getEPEFile(pattern, True)
        await self._stop()
        
    async def load_pattern(self, patterns=None):
        await self.start_ws()
        for pattern in patterns:
            self.log.info('Loading {}'.format(pattern))
            await self.load_binary_file(pattern)
        await self._stop()
            

def parse_args():
    
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Save/Load Pixelblaze Pattern')
    parser.add_argument(
        'pixelblaze_ip',
        action='store',
        type=str,
        default=None,
        help='ipaddress of pixelblaze controller (default: %(default)s)')
    parser.add_argument(
        'patterns',
        nargs='*',
        action='store',
        type=str,
        default=None,
        help='list of names or ids of patterns (None is All) (default: %(default)s)')
    parser.add_argument(
        '-a', '--action',
        nargs='?',
        default = 'save',
        const='save',
        choices=['save', 'load'],
        help='action: save or load (default: %(default)s)')
    parser.add_argument(
        '-l', '--log',
        action='store',
        type=str,
        default="./pixelblaze.log",
        help='path/name of log file (default: %(default)s)')
    parser.add_argument(
        '-D', '--debug',
        action='store_true',
        default = False,
        help='debug mode')
    parser.add_argument(
        '--version',
        action='version',
        version="%(prog)s ({})".format(__version__),
        help='Display version of this program')
    return parser.parse_args()
    
def main():
    from pixelblaze_async.utils import setup_logger, valid_ip
    arg = parse_args()
    
    if arg.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    '''
    logging.basicConfig(level=log_level, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    '''    
        
    #setup logging
    setup_logger('Pixelblaze', arg.log, level=log_level,console=True)
    global log
    log = logging.getLogger('Pixelblaze')  

    log.info("*******************")
    log.info("* Program Started *")
    log.info("*******************")
    
    log.debug('Debug Mode')

    log.info("{} Version: {}".format(sys.argv[0], __version__))
    log.info("{} Version: {}".format(PixelblazeClient.__name__, PixelblazeClient.__version__))

    log.info("Python Version: {}".format(sys.version.replace('\n','')))
    
    loop = asyncio.get_event_loop()
    loop.set_debug(arg.debug)
    
    if not valid_ip(arg.pixelblaze_ip)
        log.critical('Must supply a valid ip address, {} is not valid'.format(arg.pixelblaze_ip))
        return

    pb = PixelblazePattern(arg.pixelblaze_ip)
    
    try:
        if arg.action == 'load':
            loop.run_until_complete(pb.load_pattern(arg.patterns))
        elif arg.action == 'save':
            loop.run_until_complete(pb.save_pattern(arg.patterns))
            
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        pb.stop()
        
    finally:
        pass


if __name__ == '__main__':
    main()