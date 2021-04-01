#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 list_patterns.py
 
Pixelblaze based LED controller for APA102/SK9822 LED Strips
Working Example using PixelblazeClient
 
 MQTT interface for pixelblaze v3
 N Waterton V 1.0 16th March 2021: Initial release
'''

import sys
import logging
import asyncio
import argparse

try:
    from pixelblaze_async.PixelblazeClient import PixelblazeClient
except (ImportError, ModuleNotFoundError):
    from PixelblazeClient import PixelblazeClient
    

__version__ = "1.0.0"

class PixelblazePattern(PixelblazeClient):
    '''
    lists patterns on pixelblaze
    '''
    
    __version__ = "1.0.0"

    def __init__(self, pixelblaze_ip=None):           
        super().__init__(pixelblaze_ip)
                         
    async def list_patterns(self):
        await self.start_ws()
        patterns = await self._get_patterns()
        await self._stop()
        self.log.info('Patterns on {}({}):'.format(self.name, self.ip))
        for pattern in patterns:
            pid, name = await self._get_pattern_id_and_name(pattern, patterns)
            self.log.info('pid: {} name: {}'.format(pid, name))
        self.log.info('Total of {} patterns on {}'.format(len(patterns), self.name))

def parse_args():
    
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='List Patterns on Pixelblaze')
    parser.add_argument(
        'pixelblaze_ip',
        action='store',
        type=str,
        default=None,
        help='ipaddress of pixelblaze controller (default: %(default)s)')
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
    from pixelblaze_async.utils import setup_logger
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
    
    
    pb = PixelblazePattern(arg.pixelblaze_ip)
    
    try:
        loop.run_until_complete(pb.list_patterns())
            
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        pb.stop()
        
    finally:
        pass


if __name__ == '__main__':
    main()