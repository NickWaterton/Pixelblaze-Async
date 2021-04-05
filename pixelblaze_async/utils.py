#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 utils.py
 
 A utility library for pixelbalze.py.  Requires Python 3

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
 N Waterton v 1.0.1 5th April 2021: Changed pixelblaze_ip to be a list of ip's
'''

__version__ = "1.0.1"

import sys
import logging
from logging.handlers import RotatingFileHandler
import argparse
import re, base64

def parse_args():
    
    #-------- Command Line -----------------
    parser = argparse.ArgumentParser(
        description='Forward MQTT data to Pixelblaze controller')
    parser.add_argument(
        'pixelblaze_ip',
        nargs='*',
        action='store',
        type=str,
        const=None,
        default=None,
        help='ipaddress of pixelblaze controller (or list of controllers) (default: %(default)s)')
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
        '-b', '--broker',
        action='store',
        type=str,
        default=None,
        help='ipaddress of MQTT broker (default: %(default)s)')
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
    
def decode_base64(data, altchars=b'+/'):
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    try:
        data = re.sub(rb'[^a-zA-Z0-9%s]+' % altchars, b'', data)  # normalize
        missing_padding = len(data) % 4
        if missing_padding:
            data += b'='* (4 - missing_padding)
        return base64.b64decode(data, altchars)
    except Exception as e:
        pass
    return None
    
def setup_logger(logger_name, log_file, level=logging.DEBUG, console=False):
    try: 
        l = logging.getLogger(logger_name)
        formatter = logging.Formatter('[%(asctime)s][%(levelname)5.5s](%(name)-20s) %(message)s')
        if log_file is not None:
            fileHandler = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=10000000, backupCount=10)
            fileHandler.setFormatter(formatter)
        if console == True:
            #formatter = logging.Formatter('[%(levelname)1.1s %(name)-20s] %(message)s')
            streamHandler = logging.StreamHandler()
            streamHandler.setFormatter(formatter)

        l.setLevel(level)
        if log_file is not None:
            l.addHandler(fileHandler)
        if console == True:
          l.addHandler(streamHandler)
             
    except Exception as e:
        print("Error in Logging setup: %s - do you have permission to write the log file??" % e)
        sys.exit(1)