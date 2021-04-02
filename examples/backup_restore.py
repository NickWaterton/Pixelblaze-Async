#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 backup_restore_pattern.py
 
Pixelblaze based LED controller for APA102/SK9822 LED Strips
Working Example using PixelblazeClient

NOTE: this implements a different way of using an async library!
 
 MQTT interface for pixelblaze v3
 N Waterton V 1.0 16th March 2021: Initial release
'''

import sys, json
import logging
import asyncio
import argparse
import os.path
import ipaddress
from  zipfile import ZipFile, is_zipfile

try:
    from pixelblaze_async.PixelblazeClient import PixelblazeClient
except (ImportError, ModuleNotFoundError):
    from PixelblazeClient import PixelblazeClient
    

__version__ = "1.0.0"

def valid_ip(address):
    try: 
        ipaddress.ip_address(address)
        return True
    except:
        return False

class PixelblazeBackup(PixelblazeClient):
    '''
    backup/Restore patterns
    NOTE this adds a file called 'index.txt' to the zip archive created, this contains the list of pid and names backed up
    so there will always be one more file in the archive than there are patterns.
    You can retrieve and list from zip files missing `index.txt`, but the names of the patterns will not be displayed,
    just the PID's
    'index.txt' is a text file that can be read as a reference for pid's to names in the archive.
    '''
    
    __version__ = "1.0.0"
    
    
    def __init__(self, pixelblaze_ip=None, filename=None, patterns=None, action='list'):           
        super().__init__(pixelblaze_ip)
        self.filename = filename
        self.action = action
        self.actions  = { 'backup' : self.backup_patterns,
                          'restore': self.restore_pattern,
                          'list'   : self.list_zip
                        }
        self.log.info('Action is: {}'.format(self.action))
        self.patterns = patterns
        
    def __await__(self):
        return self.init().__await__()
        
    async def init(self):
        '''
        get filename and run the selected action
        '''
        self.filename = await self.get_filename(self.filename)
        if not self.filename: return
        await self.actions[self.action]()
                 
    async def backup_patterns(self):
        '''
        backup a list of patterns or all patterns to zip file
        '''
        try:
            backup_patterns = await self.get_backup_patterns()
            with ZipFile(self.filename, 'w') as myzip:
                myzip.writestr('index.txt', json.dumps({pid: value[0] for pid, value in backup_patterns.items()}, indent=2))
                for pid, value in backup_patterns.items():
                    myzip.writestr(pid, value[1])
                    self.log.info('Added {} {:30.30} to {}'.format(pid, value[0], self.filename))
            self.log.info('Backup done: {}'.format(self.filename))
            info = self.list_zip_contents()
            self.log.info('{} files backed up to {}'.format(len(info), self.filename))
        except Exception as e:
            self.log.error(e)
        
    async def restore_pattern(self):
        '''
        restore a list of patterns or all patterns from zip file
        '''
        await self.start_ws()
        try:
            restore_patterns = await self.get_patterns_to_restore()
            with ZipFile(self.filename) as myzip:
                for pid, name in restore_patterns.items():
                    if pid != 'index.txt':
                        self.log.info('Restoring {}, {:30.30} to {}'.format(pid, name, self.ip))
                        binary = myzip.read(pid) 
                        await self.load_binary_file(pid, binary)

            self.log.info('{} files restored from {}'.format(len(restore_patterns), self.filename))
        except Exception as e:
            self.log.error(e)
        await self._stop()
        
    async def list_zip(self):
        '''
        list contents of zip file
        '''
        self.log.info('Contents of zip file: {}'.format(self.filename))
        info = self.list_zip_contents()
        self.log.info('{} files in file {}'.format(len(info), self.filename))
        
    async def get_backup_patterns(self):
        '''
        downloads patterns to back up.
        returns dictionary of binary files
        '''
        backup_patterns = {}
        await self.start_ws()
        #this takes a while (if it's a long list) so increase cache timeout (or we will retrieve the pattern list every 5 seconds)
        self.cache_timeout = 30
        self.log.info('Backing up {}({}) to {}'.format(self.name, self.ip, self.filename))
        try:
            if not self.patterns:
                self.patterns = await self._get_patterns()
            for pattern in self.patterns:
                pid, name = await self._get_pattern_id_and_name(pattern)
                if not all([pid, name]):
                    self.log.warning('pattern {} Not found'.format(pattern))
                    continue
                binary = await self.save_binary_file(pid)
                if binary:
                    backup_patterns[pid] = (name, binary)
        except Exception as e:
            self.log.error(e)
        await self._stop()
        return backup_patterns
        
    async def get_patterns_to_restore(self):
        '''
        looks up pattern pid and name to restore from index if there is one
        if patterns is [], just loads index into restore_patterns.
        returns restore_patterns
        '''
        restore_patterns = {}
        with ZipFile(self.filename) as myzip:
            try:
                patterns_txt = myzip.read('index.txt')
                patterns = json.loads(patterns_txt)
                if not self.patterns:
                    restore_patterns = patterns.copy()
                else:
                    restore_patterns = {pid:name for p in self.patterns for pid, name in patterns.items() if p in [pid, name]}
            except Exception as e:
                self.log.error(e)
                restore_patterns = {file.filename:'Unknown' for file in myzip.infolist()}
        return restore_patterns 
               
    async def get_filename(self, filename=None):
        '''
        check filename is valid.
        Starts websocket to get pb's name to generate a filename if it
        isn't defined.
        '''
        if self.filename: 
            return self.check_filename(self.filename)
        await self.start_ws()
        return self.check_filename(self.name)
        
    def check_filename(self, filename):
        '''
        validate the filename
        '''
        if not filename.endswith('.zip'):
            filename+='.zip'
        if (not os.path.isfile(filename) or not is_zipfile(filename)) and self.action in ['list', 'restore']:
            self.log.warning('{} is not a valid zip file'.format(filename))
            filename = None
        return filename
        
    def list_zip_contents(self):
        '''
        prety print zip file contants
        uses 'index.txt' to look up pattern names from pid
        '''
        with ZipFile(self.filename) as myzip:
            info = myzip.infolist()
            try:
                patterns_txt = myzip.read('index.txt')
                patterns = json.loads(patterns_txt)
            except Exception as e:
                self.log.error(e)
                patterns = {}
        for file in info:
            name = patterns.get(file.filename, 'UNKNOWN')
            self.log.info('file: {:17}, name: {:30.30}, date: {} size: {}'.format(file.filename, name, self.format_date(file.date_time), file.file_size))
        return info
        
    def format_date(self, date):
        '''
        nice date formating
        '''
        return '{}/{:0>2}/{:0>2} {:0>2}:{:0>2}:{:0>2}'.format(*date)


def parse_args():
    
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Backup/Restore/List Pixelblaze Patterns to/from Zip file')
    parser.add_argument(
        'pixelblaze_ip',
        action='store',
        type=str,
        default=None,
        help='ipaddress of pixelblaze controller (default: %(default)s)')
    parser.add_argument(
        '-f', '--filename',
        action='store',
        type=str,
        default=None,
        help='filename to backup/restore from (default: %(default)s)')
    parser.add_argument(
        '-p', '--patterns',
        nargs='*',
        action='store',
        type=str,
        default=None,
        help='list of names or ids of patterns to backup/restore (None is All) (default: %(default)s)')
    parser.add_argument(
        '-a', '--action',
        nargs='?',
        default = 'list',
        const='list',
        choices=['backup', 'restore', 'list'],
        help='action: backup, restore or list (default: %(default)s)')
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
    
async def main():
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
    
    if not valid_ip(arg.pixelblaze_ip): #if it's not an ip, must be a filename
        log.warning('{} is not a valid ip so using it as filename and action is list'.format(arg.pixelblaze_ip))
        arg.filename = arg.pixelblaze_ip
        arg.pixelblaze_ip = None
        arg.action = 'list' #list is the only thing allowed if we don't have an ip address
        
    try:
    
        pb = await PixelblazeBackup(arg.pixelblaze_ip, arg.filename, arg.patterns, arg.action)
            
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        await pb._stop()
        
    finally:
        pass


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())