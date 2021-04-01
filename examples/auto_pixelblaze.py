#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 auto_pixelblaze.py
 
Pixelblaze based LED controller for APA102/SK9822 LED Strips
Working Example using PixelblazeEnumerator
 
 MQTT interface for pixelblaze v3
 N Waterton V 1.0 16th March 2021: Initial release
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

__version__ = "1.0.0"

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

async def pixelblaze_connector(pb_enum, arg):
    '''
    finds and connect/disconnect pixelblase controllers
    '''
    connections = {}
    while not pb_enum._exit:
        try:
            #add new pb
            for ip in [v["address"][0] for v in pb_enum.devices.values()]:
                if ip not in connections.keys():
                    log.info('Adding pb: {}'.format(ip))
                    connections[ip] = PixelblazeClient(ip, arg.user, arg.password, arg.broker, arg.port, arg.topic, arg.feedback, arg.json_out, poll=arg.poll_interval, log=log)
                    await connections[ip].start()
                    
            #remove old pb        
            for ip, pb in connections.copy().items():
                if ip not in [v["address"][0] for v in pb_enum.devices.values()]:
                    log.info('Removing pb: {}'.format(ip))
                    await pb._stop()    #note do NOT use pb.stop() here
                    del connections[ip]
                    
            #list pb devices and status
            for k, v in connections.items():
                log.info('{}({}) connected: {}'.format(v.name, k, await v.getWSConnected()))
            log.info('{} pixelblazes, {} connected'.format(len(connections), len([v for v in connections.values() if await v.getWSConnected()])))
            await asyncio.sleep(pb_enum.LIST_CHECK_INTERVAL)
        except asyncio.CancelledError:
            break

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
    
    
    pb_enum = PixelblazeEnumerator(log=log)
    
    try:
        asyncio.gather(*[pb_enum.start(), pixelblaze_connector(pb_enum, arg)], return_exceptions=True)
        loop.run_forever()
            
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        pb_enum.stop()
        
    finally:
        pass


if __name__ == '__main__':
    main()