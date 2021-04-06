#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 auto_pixelblaze.py
 
Pixelblaze based LED controller for APA102/SK9822 LED Strips
Working Example using PixelblazeEnumerator
 
 MQTT interface for pixelblaze v3
 N Waterton V 1.0 16th March 2021: Initial release
 N Waterton V1.0.1 6th april 2021: significant speedups
'''

import sys
import logging
import asyncio
import argparse

try:
    from pixelblaze_async.PixelblazeClient import PixelblazeClient
    from pixelblaze_async.PixelblazeEnumerator import PixelblazeEnumerator
except (ImportError, ModuleNotFoundError):
    from PixelblazeClient import PixelblazeClient
    from PixelblazeEnumerator import PixelblazeEnumerator

__version__ = "1.0.1"

def parse_args():
    
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Forward MQTT data to Pixelblaze controller')
    parser.add_argument(
        '-b', '--broker',
        action='store',
        type=str,
        default=None,
        help='ipaddress of MQTT broker (default: %(default)s)')
    parser.add_argument(
        '-t', '--topic',
        action='store',
        type=str,
        default="/pixelblaze/command",
        help='MQTT Topic to send commands to, (can use # '
             'and +) default: %(default)s)')
    parser.add_argument(
        '-T', '--feedback',
        action='store',
        type=str,
        default="/pixelblaze/feedback",
        help='Topic on broker to publish feedback to (default: '
             '%(default)s)')

    parser.add_argument(
        '-p', '--port',
        action='store',
        type=int,
        default=1883,
        help='MQTT broker port number (default: %(default)s)')
    parser.add_argument(
        '-U', '--user',
        action='store',
        type=str,
        default=None,
        help='MQTT broker user name (default: %(default)s)')
    parser.add_argument(
        '-P', '--password',
        action='store',
        type=str,
        default=None,
        help='MQTT broker password (default: %(default)s)')
    parser.add_argument(
        '-poll', '--poll_interval',
        action='store',
        type=int,
        default=0,
        help='Polling interval (0=off) (default: %(default)s)')
    parser.add_argument(
        '-l', '--log',
        action='store',
        type=str,
        default="./pixelblaze.log",
        help='path/name of log file (default: %(default)s)')
    parser.add_argument(
        '-J', '--json_out',
        action='store_false',
        default = True,
        help='publish topics as json (vs individual topics) (default: %(default)s)')
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
    
class PixelblazeConnector(PixelblazeEnumerator):

    __version__ = '1.0.1'

    def __init__(self, arg):
        super().__init__()
        self.arg = arg
        self.connections = {}
        
    async def remove_devices(self):
        #remove old pb 
        for ip, pb in self.connections.copy().items():
            if ip not in [v["address"][0] for v in self.devices.values()]:
                self.log.info('Removing pb: {}'.format(ip))
                await pb._stop()    #note do NOT use pb.stop() here
                del self.connections[ip]
        
    async def list_devices(self):
        #list pb devices and status
        while not self._exit:
            try:
                await self.remove_devices()
                for k, v in self.connections.items():
                    self.log.info('{}({}) connected: {}'.format(v.name, k, await v.getWSConnected()))
                self.log.info('{} pixelblazes, {} connected'.format(len(self.connections), len([v for v in self.connections.values() if await v.getWSConnected()])))
                await asyncio.sleep(self.LIST_CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
        
    async def connect_pb(self, ip):
        self.log.info('Adding pb: {}'.format(ip))
        self.connections[ip] = PixelblazeClient(ip, self.arg.user,
                                                    self.arg.password,
                                                    self.arg.broker,
                                                    self.arg.port,
                                                    self.arg.topic,
                                                    self.arg.feedback,
                                                    self.arg.json_out,
                                                    poll=self.arg.poll_interval)
        await self.connections[ip].start()

    async def discovery(self):
        '''
        finds and connect/disconnect pixelblase controllers
        '''
        await self.start()
        self.loop.create_task(self.list_devices())
        while not self._exit:
            try:
                await self.new_data.wait()
                #add new pb
                for ip in [v["address"][0] for v in self.devices.values()]:
                    if ip not in self.connections.keys():
                        await self.connect_pb(ip)
                        
                self.new_data.clear()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.exception(e)
                
        self.log.info('Discovery exited')

def main():
    try:
        from pixelblaze_async.utils import setup_logger
    except (ImportError, ModuleNotFoundError):
        from utils import setup_logger
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
    log.info("{} Version: {}".format(PixelblazeEnumerator.__name__, PixelblazeEnumerator.__version__))

    log.info("Python Version: {}".format(sys.version.replace('\n','')))
    
    loop = asyncio.get_event_loop()
    loop.set_debug(arg.debug)
    
    
    pb_enum = PixelblazeConnector(arg)
    
    try:
        asyncio.gather(pb_enum.discovery(), return_exceptions=True)
        loop.run_forever()
            
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        pb_enum.stop()
        
    finally:
        pass


if __name__ == '__main__':
    main()