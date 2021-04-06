#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 PixelblazeEnumerator.py
 
 Many thanks to JEM (ZRanger1) for https://github.com/zranger1/pixelblaze-client
 from where some of the methods were taken

 A library that presents a simple, asynchronous interface for communicating with and
 controlling Pixelblaze LED controllers.  Requires Python 3

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
 N Waterton V 1.0.0 16th March 2021: Initial release
 N Waterton V 1.0.1 6th April 2021; Minor fixes
'''

__version__ = "1.0.1"

import time, sys, struct
import logging
import asyncio

class PixelblazeProtocol:
    '''
    asyncio UDP Client class
    '''
    
    def __init__(self, _process_data, log=None):
        if log:
            self.log = log
        else:
            self.log = logging.getLogger("Pixelblaze.{}".format(__class__.__name__))
        self._process_data = _process_data

    def connection_made(self, transport):
        self.transport = transport
        self.log.info('UDP connection made')
        
    def error_received(self, exc):
        self.log.error('Error received: {}'.format(exc))

    def connection_lost(self, exc):
        self.log.info("UDP Connection closed")

    def datagram_received(self, data, addr):
        try:
            self.log.debug("Received {} bytes of UDP data from: {} : {}".format(len(data), addr, data))
            self._process_data(data, addr)
        except Exception as e:
            self.log.warning('Error receiving UDP data: {}'.format(e))
            self.log.info('Received {} from {}'.format(data, addr))
        
class PixelblazeEnumerator:
    """
    Async verion of PixelblazeEnumerator
    Listens on a network to detect available Pixelblazes, which the user can then list
    or open as Pixelblaze objects.  Also provides time synchronization services for
    running synchronized patterns on a network of Pixelblazes.
    """
    PORT = 1889
    SYNC_ID = 890
    BEACON_PACKET = 42
    TIMESYNC_PACKET = 43
    DEVICE_TIMEOUT = 30     #in seconds
    LIST_CHECK_INTERVAL = 5 #in seconds

    __version__ = '1.0.1'

    def __init__(self, hostIP="0.0.0.0", log=None):
        """    
        Create an object that listens continuously for Pixelblaze beacon
        packets, maintains a list of Pixelblazes and supports synchronizing time
        on multiple Pixelblazes to allows them to run patterns simultaneously.
        Takes the IPv4 address of the interface to use for listening on the calling computer.
        Listens on all available interfaces if addr is not specified.
        """
        if log:
            self.log = log
        else:
            self.log = logging.getLogger("Pixelblaze.{}".format(__class__.__name__))
        self.loop = asyncio.get_event_loop()
        self.hostIP = hostIP
        self.transport = None
        self._exit = False
        self.devices = {}
        self.autoSync = False
        self.new_data = asyncio.Event()   #event trigger for new data
        # must run async self.start()

    def __del__(self):
        self.stop()
        
    def _time_in_millis(self):
        """
        Utility Method: Returns last 32 bits of the current time in milliseconds
        """
        return int(round(time.time() * 1000)) % 0xFFFFFFFF

    def _unpack_beacon(self, data):
        """
        Utility Method: Unpacks data from a Pixelblaze beacon
        packet, returning a 3 element list which contains
        (packet_type, sender_id, sender_time)
        NOTE have to use < (littlendian) or the Long size is OS dependent
        """
        return struct.unpack("<LLL", data)

    def _pack_timesync(self, sender_id, sender_time):
        """
        Utility Method: Builds a Pixelblaze timesync packet from
        supplied data.
        NOTE have to use < (littlendian) or the Long size is OS dependent
        """
        return struct.pack("<LLLLL", self.TIMESYNC_PACKET, self.SYNC_ID,
                           self._time_in_millis(), sender_id, sender_time)
    
    def _set_timesync_id(self,id):
        """Utility Method:  Sets the PixelblazeEnumerator object's network
           id for time synchronization. At the moment, any 32 bit value will
           do, and calling this method does (almost) nothing.  In the
           future, the ID might be used to determine priority among multiple time sources. 
        """
        self.SYNC_ID = id

    def setDeviceTimeout(self, s):
        """
        Sets the interval in milliseconds which the enumerator will wait without
        hearing from a device before removing it from the active devices list.
        
        The default timeout is 30 (30 seconds).
        """
        self.DEVICE_TIMEOUT = s

    def enableTimesync(self):
        """
        Instructs the PixelblazeEnumerator object to automatically synchronize
        time on all Pixelblazes. (Note that time synchronization
        is off by default when a new PixelblazeEnumerator is created.)
        """
        self.autoSync = True

    def disableTimesync(self):
        """
        Turns off the time synchronization -- the PixelblazeEnumerator will not
        automatically synchronize Pixelblazes. 
        """
        self.autoSync = False
            
    async def start(self):
        '''
        start UDP listener on self.hostIP address, port = self.PORT
        and start updater.
        '''
        try:
            if self.transport: return 
            self.log.info('starting up UDP Server')
            self.transport, protocol = await self.loop.create_datagram_endpoint(
                lambda: PixelblazeProtocol(self._process_data),local_addr=(self.hostIP, self.PORT))
            self.log.info('Pixelblaze Discovery Server listening on {}:{} '.format(self.hostIP, self.PORT))
            self.loop.create_task(self._updatePixelblazeList())
        except asyncio.CancelledError:
            pass

    def stop(self):
        """
        Stop listening for datagrams,  close socket.
        """
        try:
            self.loop.run_until_complete(self._disconnect())
        except RuntimeError:
            self.loop.create_task(self._disconnect())
    
    async def _disconnect(self):
        self._exit = True
        if self.transport:          #UDP disconnect
            self.transport.abort()
        tasks = [t for t in asyncio.Task.all_tasks() if t is not asyncio.Task.current_task()]
        [task.cancel() for task in tasks]
        self.log.info("Cancelling {} outstanding tasks".format(len(tasks)))
        await asyncio.gather(*tasks, return_exceptions=True)

    def _send_timesync(self, sender_id, sender_time, addr):
        """
        Utility Method: Composes and sends a timesync packet to a single Pixelblaze
        """
        try:
            self.transport.sendto(self._pack_timesync(sender_id,sender_time), addr)

        except exception as e:
            self.log.error(e)
            self.stop()

    def _process_data(self, data, addr):
        """
        Internal Method: Datagram listener thread handler -- loop and listen.
        """
        try:
            self.new_data.clear()
            # when we receive a beacon packet from a Pixelblaze,
            # update device record and timestamp in our device list
            pkt = self._unpack_beacon(data)
            if pkt[0] == self.TIMESYNC_PACKET:   # always defer to other time sources
                self.autoSync = False
            elif pkt[0] == self.BEACON_PACKET:
                #add pixelblaze to list of devices, pkt{1] is sender id
                if pkt[1] not in self.devices.keys():
                    self.log.info('Found Pixelblaze: {}'.format(addr))
                self.devices[pkt[1]] = {"address"    : addr,
                                        "timestamp"  : time.time(),
                                        "sender_id"  : pkt[1],
                                        "sender_time": pkt[2]}
                
                # immediately send timesync if enabled
                if self.autoSync:
                    self._send_timesync(pkt[1], pkt[2], addr)
                    
            self.new_data.set()        
            
        except Exception as e:
            self.log.exception(e)
        
    async def _updatePixelblazeList(self):
        try:
            while not self._exit:
                # remove devices we haven't seen in a while
                for dev, record in self.devices.copy().items():
                    if time.time() - record["timestamp"] >= self.DEVICE_TIMEOUT:
                        del self.devices[dev]
                self.log.debug('PixelblazeList: {}'.format(self.getPixelblazeList()))
                await asyncio.sleep(self.LIST_CHECK_INTERVAL)
        except asyncio.CancelledError:
            pass

    def getPixelblazeList(self):
        return [record["address"][0] for record in self.devices.values()] #list of ip addresses