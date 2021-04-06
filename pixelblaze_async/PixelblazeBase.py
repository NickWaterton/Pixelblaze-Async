#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 PixelblazeBase.py
 
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
 N Waterton V 1.0.1 5th april 2021: Minor fixes.
'''

__version__ = "1.0.1"

import sys, re, os
from ast import literal_eval
import logging
from logging.handlers import RotatingFileHandler
import socket
import paho.mqtt.client as mqtt
import json
import asyncio

import aiohttp

class PixelblazeBase():
    '''
    Async Python 3 websocket class to connect to PixelBlase controller
    receives commands/sends data to MQTT broker
    '''
    
    data_type = {None                   :0,
                 'save_program_source'  :1,
                 'code_data'            :3,
                 'thumbnail_jpg'        :4,
                 'preview_frame'        :5,
                 'source_data'          :6,
                 'program_list'         :7,
                 'pixel_map'            :8,
                 'output_board_config'  :9,}
                  
    START = 1
    CONT  = 2
    END   = 4

    invalid_commands = ['start', 'stop', 'subscribe', 'start_ws']
    
    __version__ = "1.0.1"

    def __init__(self, pixelblaze_ip=None,
                       user=None,
                       password=None,
                       broker=None,
                       port=1883,
                       topic='/pixelblaze/command',
                       pubtopic='/pixelblaze/feedback',
                       json_out=True,
                       timeout=30.0,
                       poll=0,
                       log=None):
                       
        self.autolog = False
        if log:
            self.log = log
        else:
            self.log = logging.getLogger("Pixelblaze.{}".format(__class__.__name__))
            self.autolog = True
        self.debug = False
        if self.log.getEffectiveLevel() == logging.DEBUG:
            self.debug = True
        self.loop = asyncio.get_event_loop()
        if pixelblaze_ip:
            self.ws_url = 'ws://{}:81/'.format(pixelblaze_ip)
            self.ip = pixelblaze_ip
        else:
            self.ws_url =  None
            self.ip = None
        self.timeout = timeout
        self.poll = poll
        self.client = None
        self.user = user
        self.password = password
        self.broker = broker
        self.port = port
        self.topic = topic if not topic.endswith('/#') else topic[:-2]
        self.topic_override = None    #override for publish topic
        self.pubtopic = pubtopic
        self.publish_name = True
        self._publish_enabled = True
        self.json_out=json_out
        self.delimiter = '\='
        self.name = None
        self.mqttc = None
        self.ws = None
        self.auto_reconnect = False
        self.flash_save_enabled = False
        self._exit = False
        self.tasks = {}
        self.cache = {}
        self.cache_timeout = 5  #5 second timeout on cache, set to 0 to disable cache
        self.polling = [self._get_hardware_config]
        self.history = {}
        self.bin_data = None
        self.q_data = False
        self.q_binary = False
        self.method_dict = {func:getattr(self, func)  for func in dir(self) if callable(getattr(self, func)) and not func.startswith("_")}
            
        self.q = asyncio.Queue()
        self.json_q = asyncio.Queue() 
        self.binary_q = asyncio.Queue()
        
    async def setIP(self, ip=None):
        if ip:
            self.ip = ip
            self.ws_url = 'ws://{}:81/'.format(ip)
            self.name = None
            if self.getWSConnected():
                await self.ws.close()
            await self._setup_client()
        return self.ip
        
    async def getIP(self):
        return self.ip
        
    async def _setup_client(self):
        await self._waitForWS()
        while not self.name:
            if not await self._get_hardware_config():
                await asyncio.sleep(1)
        self._connect_client()
            
    def _connect_client(self):
        if not self.broker: return
        if self._MQTT_connected: return
        try:
            # connect to broker
            self.log.info('Connecting to MQTT broker: {}'.format(self.broker))
            self.mqttc = mqtt.Client()
            # Assign event callbacks
            self.mqttc.on_message = self._on_message
            self.mqttc.on_connect = self._on_connect
            self.mqttc.on_disconnect = self._on_disconnect
            if self.user and self.password:
                self.mqttc.username_pw_set(self.user, self.password)
            self.mqttc.will_set(self._get_pubtopic('status'), payload="Offline", qos=0, retain=False)
            self.mqttc.connect(self.broker, self.port, 60)
            self.mqttc.loop_start()
        except socket.error:
            self.log.error("Unable to connect to MQTT Broker")
            self.mqttc = None
        return self.mqttc
        
    def subscribe(self, topic, qos=0):
        '''
        utiltity to subscribe to an MQTT topic
        '''
        if self._MQTT_connected:
            topic = topic.replace('//','/')
            self.log.info('subscribing to: {}'.format(topic))
            self.mqttc.subscribe(topic, qos)
            
    def unsubscribe(self, topic):
        '''
        utiltity to unsubscribe from an MQTT topic
        '''
        if self._MQTT_connected:
            topic = topic.replace('//','/')
            self.log.info('unsubscribing from: {}'.format(topic))
            self.mqttc.unsubscribe(topic)
        
    @property
    def _MQTT_connected(self):
        return bool(self.mqttc.is_connected() if self.mqttc else False)
        
    async def _waitForMQTT(self, timeout=0):
        '''
        Utility to wait for MQTT connection, with optional timeout
        returns false if not broker defined
        '''
        if not self.broker: return False
        timeout = timeout if timeout else 1000000
        count = 0
        while not self._MQTT_connected and count < timeout:
            await asyncio.sleep(1)
            count += 1
        return self._MQTT_connected
        
    def _on_connect(self, client, userdata, flags, rc):
        self.log.info('MQTT broker connected')
        self.subscribe('{}/all/#'.format(self.topic))
        self.subscribe('{}/{}/#'.format(self.topic, self.name))
        self.history = {}
        
    def _on_disconnect(self, mosq, obj, rc):
        self.log.warning('MQTT broker disconnected')
        
    def _on_message(self, mosq, obj, msg):
        #self.log.info(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
        asyncio.run_coroutine_threadsafe(self.q.put(msg), self.loop)    #mqtt client is running in a different thread
        
    def _get_pubtopic(self, topic=None):
        pubtopic = self.pubtopic
        if self.name and self.publish_name:
            pubtopic = '{}/{}'.format(pubtopic,self.name)
        if topic:
            pubtopic = '{}/{}'.format(pubtopic, topic)
        return pubtopic
            
    def _publish(self, topic=None, message=None):
        if self.mqttc is not None and message is not None and self._publish_enabled:
            pubtopic = self._get_pubtopic(topic)
            self.log.info("publishing item: {}: {}".format(pubtopic, self._truncate_bytes(message)))
            self.mqttc.publish(pubtopic, str(message))
               
    def _decode_topics(self, state, prefix=None):
        '''
        decode json data dict, and _publish as individual topics to
        brokerFeedback/topic the keys are concatenated with _ to make one unique
        topic name strings are expressly converted to strings to avoid unicode
        representations
        '''
        for k, v in state.items():
            if isinstance(v, dict):
                if prefix is None:
                    self._decode_topics(v, k)
                else:
                    self._decode_topics(v, '{}_{}'.format(prefix, k))
            else:
                if isinstance(v, list):
                    newlist = []
                    for i in v:
                        if isinstance(i, dict):
                            for ki, vi in i.items():
                                newlist.append((str(ki), vi))
                        else:
                            newlist.append(str(i))
                    v = newlist
                if prefix is not None:
                    k = '{}_{}'.format(prefix, k)
                 
                if self._has_changed(k, v):
                    self._publish(k, str(v))
                
    def _has_changed(self, k, v):
        '''
        checks to see if value has changed, returns True/False
        '''
        v = str(v)
        previous = self.history.get(k)
        if previous != v:
            self.history[k] = v
            return True
        return False
        
    async def _pub_status(self):
        '''
        publish status every 60 seconds
        if MQTT disconnects, LWT will update to 'Offline'
        '''
        try:
            while not self._exit:
                if self.ws:
                    self._publish('status', 'Online')
                else:
                    self._publish('status', 'Disconnected')
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass
        
    async def _poll_status(self):
        '''
        publishes getHardwareConfig every self.poll seconds
        '''
        try:
            while not self._exit:
                await asyncio.sleep(self.poll)
                self.log.debug('Polling...')
                for cmd in self.polling:
                    await cmd()
        except asyncio.CancelledError:
            pass
        
    async def _process_q(self):
        '''
        Main MQTT command processing loop, run until program exit
        '''
        self._exit = False
        while not self._exit:
            try:
                if self.q.qsize() > 0 and self.debug:
                    self.log.warning('Pending event queue size is: {}'.format(self.q.qsize()))
                msg = await self.q.get()
                
                command, args = self._get_command(msg)
                try:
                    value = await self. _execute_command(command, args)
                except Exception as e:
                    self.log.error(e)
                    value = None
                    
                if self.topic_override: #override the topic tp publish to
                    command = self.topic_override
                    self.topic_override = None
                self._publish(command, value)
                    
                self.q.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.exception(e)
                
    def _get_command(self, msg):
        '''
        extract command and args from MQTT msg
        '''
        command = args = None
        topic_command = msg.topic.split('/')[-1]
        msg_command = msg.payload.decode('UTF-8')
            
        if topic_command in self.method_dict.keys():
            command = topic_command
            #parse arg
            args = re.split(self.delimiter, msg_command)
            try:
                args = [literal_eval(v) if re.match('\[|\{|\(|True|False|\d',v) else v for v in args]
            except Exception as e:
                if self.debug:
                    self.log.warning('error parsing args: {}'.format(e))
                
            args = self._filter_list(args)
             
        elif msg_command in self.method_dict.keys():
            command = msg_command
            
        else:
            #undefined
            cmd = topic_command if topic_command not in [self.name, 'all'] else msg_command
            if cmd not in self.invalid_commands:
                self.log.warning('Received invalid commnd: {}'.format(cmd))
            
        return command, args
        
    async def _execute_command(self, command, args):
        '''
        execute the command (if any) with args (if any)
        return value received (if any)
        '''
        value = None
        if command:
            if command in self.invalid_commands:
                self.log.warning("can't run {} from MQTT".format(command))
                return None
            try:
                self.log.info('Received command: {}'.format(command))
                self.log.info('args: {}'.format(args))
                
                if args:
                    value = await self.method_dict[command](*args)
                else:
                    value = await self.method_dict[command]()
            except Exception as e:
                self.log.warning('Command error {} {}: {}'.format(command, args, e))
            self.log.info('return value: {}'.format(self._truncate_bytes(value)))
        return value
        
    def _filter_list(self, fl):
        '''
        utility function to strip '' out of lists, and trim leading/trailing spaces
        returns filtered list
        '''
        return list(filter(lambda x: (x !=''), [x.strip() if isinstance(x, str) else x for x in fl]))
        
    async def _expect(self, keys=None, all=False, binary=0x00):
        '''
        waits for specific key in data queues, returns data if found
        if all is set, returns the whole dict the key is found in
        otherwise returns just the key value
        if binary is a byte value, returns the binary data starting with that byte
        '''
        json_data = {}
        result = {}
        bin_data = bytes([binary])
        if keys:
            if isinstance(keys, str):   #make list
                keys = [keys]
            for key in keys:
                while not key in result.keys():
                    result = await self.json_q.get()
                    self.json_q.task_done()
                if all:
                    json_data.update(result)
                elif not isinstance(result[key], dict):
                    json_data.update({key: result[key]})
                else:
                    json_data.update(result[key])
                    
            self.q_data = False
        if binary:
            while bin_data[0] == binary:
                bin_data = await self.binary_q.get()
                self.binary_q.task_done()
                if bin_data[0] == binary:
                    bin_data = self._decode_binary_data(bin_data)
                    if isinstance(bin_data, dict):  #found patterns
                        break
                else:
                    bin_data = bytes([binary])
                
            self.q_binary = False 
        #handle just receiving single value
        if len(json_data.keys()) == 1 and not all:
            json_data = list(json_data.copy().values())[0]
        return json_data, bin_data
        
    def _str2bool(self, val):
        '''
        utility to convert string to bool
        '''
        if isinstance(val, str):
            val = val.lower() in ("yes", "true", "t", "1")
        return val
        
    def _decode_binary_data(self, bin_data):
        '''
        decodes binary data from chunks of binary data
        returns decoded data or original data
        uses self.bin_data as temporary data accumulator
        makes dictionary out of program_list data
        '''
        data = b''
        type = [k for k, v in self.data_type.items() if v==bin_data[0]]
        self.log.debug('decoding data type: {}'.format(type[0] if type else 'unknown'))
        if self.bin_data is None:
            self.bin_data = b''
        if bin_data[1] & self.START: #start of list
            self.bin_data+= bin_data[2:]
        if bin_data[1] & self.END:   #end of list
            if bin_data[0] == self.data_type['program_list']:
                listFrame = [m.split("\t") for m in self.bin_data.decode("utf-8").split("\n")]
                data = {pat[0]:pat[1] for pat in listFrame if len(pat) == 2}
            else:
                data = self.bin_data
            self.bin_data = None
        return data if data else bin_data
        
    def _clamp(self, n):
        '''
        utility to clamp values to min 0 max 1
        '''
        return max(0, min(float(n), 1))
        
    def _byte_to_float(self, n):
        '''
        utility to convert byte values to 0-1 float
        '''
        return self._clamp(float(n/255))
        
    def _clear_cache(self):
        '''
        clears the cache
        '''
        self.cache = {}
    
    def _get_save_value(self, val):
        """
        Utilty method: Returns a boolean that can be used by methods which
        can optionally save data to flash memory.  Always returns False if
        _enable_flash_save() has not been called on the Pixelblaze object. Otherwise
        returns a boolean reflecting the value of the boolean <val> argument.
        """
        return val if self.flash_save_enabled else False

    def _enable_flash_save(self, value=True):
        """
        IMPORTANT SAFETY TIP:
           To preserve your Pixelblaze's flash memory, which can wear out after a number of
           cycles, you must call this method before using setControls() with the
           saveFlash parameter set to True.
           If this method is not called, setControls() will ignore the saveFlash parameter
           and will not save settings to flash memory.
        """
        self.flash_save_enabled = value
        
    async def _get_patterns(self):
        '''
        returns patterns dictionary
        '''
        return await self._ws_send({"listPrograms" : True }, binary=self.data_type['program_list'], cache=True)
        
    async def _get_hardware_config(self):
        """
        Returns a dictionary containing all the available hardware configuration data
        getConfig also receives 3 binary bytes of 0x09, 0x05, 0x05 - probably markers of some kind.
        """
        result = await self._ws_send({"getConfig": True}, expect=['name', 'activeProgram'], all=True, cache=True)
        if result and not self.name:
            self.name = result.get('name', self.name)   #update pixelblaze name
            if self.autolog:
                self.log = logging.getLogger("Pixelblaze.{}.{}".format(__class__.__name__, self.name))
        return result
        
    async def _get_active_pattern(self, name=False):
        """
        Returns the ID of the pattern currently running on
        the Pixelblaze if available.  Otherwise returns an empty dictionary
        object
        """
        hw = await self._get_hardware_config()
        if name:
            return hw.get('activeProgram', {}).get('name', {}) if hw else {}
        return hw.get('activeProgram', {}).get('activeProgramId', {}) if hw else {}
            
    def _id_from_name(self, patterns, name):
        """Utility Method: Given the list of patterns and text name of a pattern, returns that pattern's ID"""
        result = [pid for pid, _name in patterns.items() if _name == name]
        return result[0] if result else None
        
    def _name_from_id(self, patterns, pid):
        """Utility Method: Given the list of patterns and pid of a pattern, returns that pattern's text name"""
        result = [name for _pid, name in patterns.items() if _pid == pid]
        return result[0] if result else None
    
    async def _get_pattern_id(self, pattern):
        """Utility Method: Returns a pattern ID if passed either a valid ID or a text name"""
        patterns = await self._get_patterns()
        if patterns:
            return pattern if pattern in patterns.keys() else self._id_from_name(patterns, pattern)
        return None
        
    async def _get_pattern_id_and_name(self, pattern, patterns=None):
        '''
        Utility Method: Returns a pattern ID and name if passed either a valid ID or a text name
        optionally can accept a patterns dictionary, so patterns does not have to fetched.
        '''
        if not patterns:
            patterns = await self._get_patterns()
        if patterns:
            if pattern in patterns.keys():
                name = self._name_from_id(patterns, pattern)
                pid = pattern if name else None 
            else:
                pid = self._id_from_name(patterns, pattern)
                name = pattern if pid else None
            return pid, name
        return None, None 
    
    async def _get_current_controls(self):
        """
        Utility Method: Returns controls for currently running pattern if
        available, None otherwise
        """
        result = await self._get_hardware_config()
        # retrieve control settings for active pattern from hardware config
        return result.get('activeProgram', {}).get('controls') if result else None
        
    async def _find_pattern_file(self, name):
        '''
        run_in_executor as this could take some timeout
        '''
        return await self.loop.run_in_executor(None, self.__find_pattern_file, name)
    
    def __find_pattern_file(self, pattern_name):
        '''
        search binary pattern files for string 'name' where name is the 
        plain text name of the pattern
        '''
        try:
            self.log.info('Looking for binary file to load')
            for root, dirs, files in os.walk(".", topdown=False):
                for name in files:
                    filename = os.path.join(root, name)
                    if filename.endswith('.bin'):
                        self.log.debug('searching {} for {}'.format(filename, pattern_name))
                        with open(filename, 'rb') as f:
                            data = f.read()
                        found = data.find(pattern_name.encode())
                        if found != -1:
                            self.log.info('found "{}" in file: {}'.format(pattern_name, filename))
                            return filename
        except Exception as e:
            self.log.exception(e)
        return None
        
    async def read_binary_file(self, filename=None, binary_only=False):
        '''
        loads a binary file (.bin) and returns the PID and binary data (as bytes)
        if the filename is not found, searches the current directory using 'filename' as 
        the pattern name.
        returns pid, binary data, or None, None.
        if binary_only is set, just returns binary data or None
        '''
        result = None,None
        if binary_only:
            result = None
        try:
            program_name = filename
            binary = None
            if not filename.endswith('.bin'):
                filename+='.bin'
            filename = os.path.basename(filename)
            if not os.path.isfile(filename):
                filename = await self._find_pattern_file(program_name)
            if not filename:
                self.log.info('Pattern/file "{}" not found'.format(program_name))
                return result
            self.log.info('Loading pattern {} from file: {}'.format(program_name, filename))
            with open(filename, 'rb') as f:
                binary = f.read()
            programId = filename.replace('.bin','')
            if binary_only:
                result = binary
            else:
                result = programId, binary
        except Exception as e:
            self.log.error(e)
        return result
        
    async def load_binary_file(self, filename=None, binary=None):
        '''
        If 'binary' is given, then load the data in 'binary' into the pixelblaze as pid 'filename'.
        if 'binary' is None, then open the file 'filename' (automatically given a '.bin' extension)
        and load that as pid 'filename'. if the file cannot be found, searches all .bin files in the
        current directory for 'pattern name' where 'pattern name' is the 'filename' passed.
        returns either the pid loaded if successful, or None.
        '''
        try:
            program_name = filename
            if not binary:
                programId, binary = await self.read_binary_file(filename)
            else:
                programId = filename.replace('.bin','')
            if not binary: return None
            form = aiohttp.MultipartWriter('form-data')
            part = form.append(binary)
            part.headers[aiohttp.hdrs.CONTENT_DISPOSITION] = 'form-data; name="data"; filename="/p/{}"'.format(programId)
            part.headers[aiohttp.hdrs.CONTENT_TYPE] = 'application/octet-stream'
            async with aiohttp.ClientSession() as session:
                #use below for debugging with test.py program
                #async with session.post('http://{}:8010/edit'.format('192.168.100.113'), data=form) as resp:
                async with session.post('http://{}/edit'.format(self.ip), data=form) as resp:
                    self.log.debug(resp.status)
                    await resp.text()
            if resp.status == 200:
                self.log.info('Pattern: {} loaded'.format(programId))
                self._clear_cache()
                return programId
            else:
                self.log.warning('Could not upload file {}'.format(filename))
        except Exception as e:
            self.log.error(e)
        return None
            
    async def save_binary_file(self, pattern=None, save=False):
        '''
        downloads the given pid or name, and returns the binary data, optionally, saves it as a binary file
        returns the binary data, or None.
        '''
        try:
            result = None
            #if not pattern:
            #    pattern = await self._get_active_pattern()
            #    self.log.info('saving current pattern: {}'.format(pattern))
            pid, name = await self._get_pattern_id_and_name(pattern)
            if not all([pid, name]):
                self.log.warning('pattern {} Not found'.format(pattern))
                return None
            self.log.debug('downloading {}, as {}'.format(name, pid))
            async with aiohttp.ClientSession() as session:
                async with session.get('http://{}/p/{}'.format(self.ip, pid)) as resp:
                    self.log.debug(resp.status)
                    result = await resp.read()
                    if resp.status == 200:
                        self.log.info('received binary file "{}" as {}'.format(name, pid)) 
                        if save:
                            fname = '{}.bin'.format(pid)
                            with open(fname, 'wb') as f:
                                f.write(result)
                            self.log.info('saved {} as file: {}'.format(name, fname))
                    self.log.debug(result)
        except Exception as e:
            self.log.exception(e)
        return result
        
    def _cache(self, key, value, cache=False):
        '''
        caches value in key for later retrieval
        '''
        if cache and key and self.cache_timeout > 0:
            self.cache[key] = value
            self.loop.call_later(self.cache_timeout, self.cache.pop, key, None)
        return value
        
    def _get_cache(self, msg):
        '''
        returns cached value if it exists, and cache key from msg
        '''
        cache_key = list(msg.keys())[0]
        self.log.debug ('cache key is: {}'.format(cache_key))
        val =  self.cache.get(cache_key)
        return val, cache_key
            
    async def _ws_send(self, msg, expect=None, timeout=10, all=False, binary=0x00, cache=False):
        '''
        sends json command, and optionally waits for result
        expect is string or list of strings to look for in the data stream.
        if all is set, all the json data is returned (if matched), otherwise, just the string as the key.
        binary is a single byte to look for as the first byte in the binary data stream
        if cache is set, the results are cached for cache_timeout seconds to speed up repeated calls to the same
        command
        '''
        val, cache_key = self._get_cache(msg)   #get cached value if it exists
        if val is not None:
            self.log.debug('returning cached value')
            return val
        if await self.getWSConnected():
            self.log.info('sending: {}'.format(msg))
            if expect:
                self.q_data = True
            if binary:
                self.q_binary = True
            await self.ws.send_json(msg)
            if expect or binary:
                try:
                    json_data, bin_data = await asyncio.wait_for(self._expect(expect, all, binary), timeout)
                    if expect and binary:
                        return json_data, bin_data
                    if expect:
                        return self._cache(cache_key, json_data, cache)
                    if binary:
                        return self._cache(cache_key, bin_data, cache)
                except asyncio.TimeoutError:
                    self.q_data = self.q_binary = False
                    self.log.warning('Timeout waiting for {}, {}'.format(expect, binary))
        if expect and binary:
            return None, None
        return None
        
    async def start_ws(self):
        '''
        Alternative start function
        starts tasks and waits for websocket connection, and name
        '''
        await self.start()
        #wait for websocket
        await self._waitForWS()
        while not self.name:
            await asyncio.sleep(1)

    async def start(self):
        if not self.ip:
            self.log.critical('Must specify an ip address to connect to')
            return
        if self.tasks: return
        try:
            self._exit = False
            self.tasks['_process_q'] = self.loop.create_task(self._process_q())
            self.tasks['_setup_client'] = self.loop.create_task(self._setup_client())
            self.tasks['_pub_status'] = self.loop.create_task(self._pub_status())
            if self.poll:
               self.tasks['_poll_status'] = self.loop.create_task(self._poll_status())
            await self.connect()
        except asyncio.CancelledError:
            pass     
                
    def stop(self):
        try:
            self.loop.run_until_complete(self._stop())
        except RuntimeError:
            self.loop.create_task(self._stop())
    
    async def _stop(self):
        self._exit = True
        await self.disconnect()
        #tasks = [t for t in asyncio.Task.all_tasks() if t is not asyncio.Task.current_task()]
        tasks = [t for t in self.tasks.values() if t is not asyncio.Task.current_task()]
        [task.cancel() for task in tasks]
        self.log.info("Cancelling {} outstanding tasks".format(len(tasks)))
        await asyncio.gather(*tasks, return_exceptions=True)

        self.tasks = {}
        self.ws = None
        if self._MQTT_connected:
            self.mqttc.disconnect()
            self.mqttc.loop_stop()
            self.mqttc = None
        self.log.info('{} stopped'.format(self.name))
            
    async def connect(self):
        if await self.getWSConnected(): return
        self.auto_reconnect = True
        try:
            self.tasks['ws'] = self.loop.create_task(self._async_websocket())
        except asyncio.CancelledError:
            pass
        
    async def disconnect(self):
        self.auto_reconnect = False
        try:
            if await self.getWSConnected():
                try:
                    await asyncio.wait_for(self.ws.close(), 5)
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            pass
        self.ws = None
        
    async def _waitForWS(self, timeout=0):
        '''
        Utility to wait for websocket connection, with optional timeout
        '''
        try:
            while not await asyncio.wait_for(self.getWSConnected(), timeout):
                await asyncio.sleep(1)
        except asyncio.TimeoutError:
            return False
        return await self.getWSConnected()
        
    def _truncate_bytes(self, data, length=12):
        if not isinstance(data, bytes) : return data
        l_data = len(data)
        return '{}{}'.format(data[:min(l_data, length)], '...' if l_data>length else '')
        
    async def getWSConnected(self):
        return bool(not self.ws.closed if self.ws else False)
        
    async def _async_websocket(self):
        if not self.ws_url:
            self.log.error('pixelblase ip is not defined')
            return
        self.log.info('Connecting websocket {}'.format(self.ws_url))
        try:
            timeout = aiohttp.ClientTimeout(total=None, connect=self.timeout)
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.ws_url, timeout=timeout, heartbeat=self.timeout) as self.ws:
                    self.log.info('Websocket Connected')
                    async for msg in self.ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            msg_json = msg.json()
                            if not self.debug:
                                self.log.info('Received: {} json data items'.format(len(msg_json)))
                            self.log.debug('Received: {}'.format(json.dumps(msg_json,indent=2)))
                            if self.q_data:
                                await self.json_q.put(msg_json)
                            if self.json_out:
                                self._publish('update', msg.data)
                            else:
                                self._decode_topics(msg_json)
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            msg_bin = msg.data
                            if self.debug:
                                l_data = len(msg_bin)
                                if not self.debug:
                                    self.log.info('Received: {} binary data bytes'.format(l_data))
                                self.log.debug('Received binary data: len: {} {}'.format(l_data, self._truncate_bytes(msg_bin)))
                            if self.q_binary:
                                await self.binary_q.put(msg_bin)
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            self.log.info('WS closed')
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            self.log.error('WS closed with Error')
                            break
                            
        except asyncio.CancelledError:
            self.ws = None
            return
        except (AssertionError, aiohttp.client_exceptions.ClientConnectorError) as e:
            self.log.error('failed to connect: {}'.format(e))
        except Exception as e:
            self.log.exception(e)
        self.log.warning('Websocket disconnected')
        self.ws = None
        if self.auto_reconnect and not self._exit:
            await asyncio.sleep(5)
            self.log.warning('Reconnecting websocket')
            await self.connect()
            