#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 clone.py
 
Pixelblaze based LED controller for APA102/SK9822 LED Strips
Working Example using PixelblazeClient
 
 MQTT interface for pixelblaze v3
 N Waterton V 1.0 16th March 2021: Initial release
 N Waterton V1.0.1 6th April 20201; added valid_ip
'''

import sys, time
import logging
import asyncio
import argparse

try:
    from pixelblaze_async.PixelblazeClient import PixelblazeClient
except (ImportError, ModuleNotFoundError):
    from PixelblazeClient import PixelblazeClient
    

__version__ = "1.0.1"

class PixelblazeClone(PixelblazeClient):
    '''
    clone pattern from one pixelblaze to another
    '''
    
    __version__ = "1.0.0"

    def __init__(self, pixelblaze_ip=None):           
        super().__init__(pixelblaze_ip)
        self.patterns = {}
        
    async def clone_pattern(self, dest_ips=[], patterns=[]):
        '''
        copy loaded pattern(s) to destination ip(s)
        '''
        await self.load_patterns(patterns)
        if not self.patterns:
            self.log.error('no patterns to clone!')
            return
        await self.send_patterns(dest_ips)
        
    async def load_patterns(self, patterns=[]):
        '''
        load patterns list from source to self.patterns
        '''
        await self.start_ws()
        try:
            patterns = await self.get_patterns(patterns)
            for pattern in patterns:
                pid, name = await self._get_pattern_id_and_name(pattern)
                if not all([pid, name]):
                    self.log.warning('pattern {} Not found'.format(pattern))
                    continue
                self.log.info('receiving {} from {}({})'.format(pid, self.name, self.ip))
                binary = await self.save_binary_file(pid)
                if binary:
                    self.patterns[pid] = binary
        except Exception as e:
            self.log.error(e)
        await self._stop()
        
    async def send_patterns(self, dest_ips=[]):
        for dest_ip in dest_ips:
            try:
                result=[]
                dest_pb = PixelblazeClone(dest_ip)
                await dest_pb.start_ws()
                for pid, binary in self.patterns.items():
                    self.log.info('sending {} to {}({})'.format(pid, dest_pb.name, dest_pb.ip))
                    res = await dest_pb.load_binary_file(pid, binary)
                    result.append(res)
            except Exception as e:
                self.log.error(e)
            await dest_pb._stop()
            self.log.info('cloned {} patterns from {}({}) to {}({})'.format(len(result), self.name, self.ip, dest_pb.name, dest_pb.ip))
        
    async def get_patterns(self, patterns=[]):
        '''
        get list of pattern ids
        '''
        if patterns:
            return patterns
        patterns = await self._get_patterns()
        return [] if not patterns else list(patterns.keys())
            

def parse_args():
    
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Clone Pixelblaze Patterns')
    parser.add_argument(
        'source_ip',
        action='store',
        type=str,
        default=None,
        help='ipaddress of source pixelblaze controller (default: %(default)s)')
    parser.add_argument(
        'destination_ips',
        nargs='+',
        action='store',
        type=str,
        default=None,
        help='list of ipaddress(s) of destination pixelblaze controller(s) (default: %(default)s)')
    parser.add_argument(
        '-p', '--patterns',
        nargs='*',
        action='store',
        type=str,
        default=None,
        help='list of names or ids of patterns to clone (None is All) (default: %(default)s)')
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
    
    if not valid_ip(arg.source_ip)
        log.critical('Must supply a valid source ip address, {} is not valid'.format(arg.source_ip))
        return
    
    for ip in arg.destination_ips:
        if not valid_ip(ip)
            log.critical('Must supply a valid destination ip address, {} is not valid'.format(ip))
            return
        if arg.source_ip == ip:
            log.error("Can't clone from {} to the same destination ip!".format(arg.source_ip))
            return
            
    if not arg.patterns:       
        log.warning( 'This will copy All patterns from {}, to {}'
                     'press ^C if this is not what is intended. '
                     'continue in 5 seconds'.format(arg.source_ip, arg.destination_ips))
        time.sleep(5)
        
    log.info('cloning pattern {} from {} to {}'.format('All' if not arg.patterns else arg.patterns, arg.source_ip, arg.destination_ips))
    
    pb = PixelblazeClone(arg.source_ip)
    
    try:
        loop.run_until_complete(pb.clone_pattern(arg.destination_ips, arg.patterns))
            
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        pb.stop()
        
    finally:
        pass


if __name__ == '__main__':
    main()