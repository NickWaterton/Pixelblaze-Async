#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 pixelblaze.py
 
 Many thanks to JEM (ZRanger1) for https://github.com/zranger1/pixelblaze-client
 from where some of the methods were taken

 A library that presents a simple, asynchronous interface for communicating with and
 controlling Pixelblaze LED controllers.  Requires Python 3, the aiohttp
 module, and the paho-mqtt module

 parts Copyright 2020 JEM (ZRanger1)
 Copyright 2021 NW (Nick Waterton)

 Permission is hereby granted, free of charge, to any person obtaining a copy of this
 software and associated documentation files (the "Software"), to deal in the Software
 without restriction, including without limitation the rights to use, copy, modify, merge,
 _publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
 to whom the Software is furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in all copies or
 substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
 BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
 AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 THE SOFTWARE.
 
 MQTT interface for pixelblaze v3
 N Waterton V 1.0 16th March 2021: Initial release
'''

__version__ = "1.0.0"

import sys
import logging
import asyncio

from PixelblazeClient import PixelblazeClient
    
def main():
    from utils import parse_args, setup_logger
    arg = parse_args()
    
    if arg.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    #setup logging
    setup_logger('Pixelblaze', arg.log, level=log_level,console=True)
    
    #logging.basicConfig(level=logging.DEBUG, 
    #    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
    
    pb = PixelblazeClient(arg.pixelblaze_ip, arg.user, arg.password, arg.broker, arg.port, arg.topic, arg.feedback, arg.json_out, poll=arg.poll_interval)
    
    try:
        asyncio.gather(pb.start(), return_exceptions=True)
        loop.run_forever()
            
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        pb.stop()
        
    finally:
        pass


if __name__ == '__main__':
    main()

