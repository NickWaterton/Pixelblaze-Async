#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 PixelblazeClient.py
 
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

'''
commands NOT implemented:
    {'savePixelMap': bool}
    {'name': 'name'}
    {'maxBrightness': num, 'save': bool}  0-100
    {'colorOrder': 'order'} 'BGR" etc
    {'ledType': num}
    {'brandName': 'name'}
    {'simpleUiMode': bool}
    {'nextProgram': bool}
    {'playlist': {'position': num}}
    {'playlist': {'id': "_defaultplaylist_",'items': list}
    {'discoveryEnable': bool, 'timezone': val} eg "America/Toronto"
    {'timezone': val} eg "America/Toronto"
    {'autoOffEnable: bool}
    {'autoOffStart': 'hrs:mins'}
    {'autoOffEnd': 'hrs:mins'}
    {'upgradeVersion': "update" or "check", 'getUpgradeState': bool}
    {'getPlaylist': "_defaultplaylist_"}
    {'deleteProgram': 'pid')
'''

__version__ = "1.0.0"

import sys, json
import base64
import logging
import socket
import asyncio

try:
    from pixelblaze_async.PixelblazeBase import PixelblazeBase
    from pixelblaze_async.lzstring import LZString
except (ImportError, ModuleNotFoundError):
    from PixelblazeBase import PixelblazeBase
    from lzstring import LZString

            
class PixelblazeClient(PixelblazeBase):
    '''
    commands for PixelblazeBase
    '''
    
    __version__ = "1.0.0"
    
    def __init__(self, pixelblase_ip=None,
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
        super().__init__(pixelblase_ip,
                             user,
                             password,
                             broker,
                             port,
                             topic,
                             pubtopic,
                             json_out,
                             timeout,
                             poll,
                             log)
                             
        self.polling.append(self.getVars)  #add getVars to poll list
                          
    async def enable_flash_save(self, value=True):
        """
        same as _enable_flash_save, but async version (callable from MQTT)
        """
        self.flash_save_enabled = value
                         
    async def waitForEmptyQueue(self, timeout_ms=1000):
        """
        Wait until the Pixelblaze's websocket message queue is empty, or until
        timeout_ms milliseconds have elapsed.  Returns True if an empty queue
        acknowldgement was received, False if timeout or error occurs.
        """
        result = await self._ws_send({"ping": True}, expect='ack', timeout=timeout_ms/1000.0)
        return bool(result)
        
    async def getHardwareConfig(self):
        """
        Returns a JSON object containing all the available hardware configuration data
        getConfig also receives 3 binary bytes of 0x09, 0x05, 0x05 - probably markers of some kind.
        """
        return await self._get_hardware_config()
        
    async def getVars(self):
        """Returns JSON object containing all vars exported from the active pattern"""
        return await self._ws_send({"getVars": True}, expect='vars')
        
    async def setVars(self, json_vars):
        """
        Sets pattern variables contained in the json_vars (JSON object) argument.
        api also supports arrays as values eg {'rgb':[0, 1.0, 0]}.
        Does not check to see if the variables are exported by the current active pattern.
        """
        await self._ws_send({"setVars" : json_vars })

    async def setVariable(self, var_name, value):
        """
        Sets a single variable to the specified value. Does not check to see if the
        variable is actually exported by the current active pattern.
        """
        await self.setVars({var_name: value})
        result = await self.getVars()
        return result.get(var_name) if result else None

    async def variableExists(self, var_name):
        """
        Returns True if the specified variable exists in the active pattern,
        False otherwise.
        """
        result = await self.getVars()
        return False if not result else bool(var_name in result.keys())
        
    async def getPatternList(self):
        """
        Returns a dictionary containing the unique ID and the text name of all
        saved patterns on the Pixelblaze
        """
        return await self._get_patterns()

    async def setActivePatternId(self, pid):
        """
        Sets the active pattern by pattern ID, without the name lookup option
        supported by setActivePattern().  This method is faster and more
        network efficient than SetActivePattern() if you already know a
        pattern's ID.
        
        It does not validate the input id, or determine if the pattern is
        available on the Pixelblaze.
        It does return True is the active pattern was set as requested, and False if it was not
        """
        result = await self._ws_send({"activeProgramId" : pid}, expect='activeProgram')
        return bool(result.get("activeProgramId") == pid) if result else False

    async def setActivePattern(self, pattern):
        """Sets the currently running pattern, using either an ID or a text name"""
        pid = await self._get_pattern_id(pattern)
        return await self.setActivePatternId(pid) if pid else None

    async def getActivePattern(self):
        """
        Returns the ID of the pattern currently running on
        the Pixelblaze if available.  Otherwise returns an empty dictionary
        object
        """
        return await self._get_active_pattern()
        
    async def getActivePatternName(self):
        """
        Returns the name of the pattern currently running on
        the Pixelblaze if available.  Otherwise returns an empty dictionary
        object
        """
        return await self._get_active_pattern(name=True)

    async def setBrightness(self, n, saveFlash=False):
        """Set the Pixelblaze's global brightness.  Valid range is 0-1"""
        save = self._get_save_value(saveFlash)
        await self._ws_send({"brightness" : self._clamp(n), 'save': save})
        
    async def getBrightness(self):
        '''
        returns current global brightness
        '''
        hw = await self.getHardwareConfig()
        return hw.get('brightness', None) if hw else None
        
    async def setSequenceTimer(self, n):
        """
        Sets number of milliseconds the Pixelblaze's sequencer will run each pattern
        before switching to the next.
        """
        await self._ws_send({"sequenceTimer" : int(n)})

    async def startSequencer(self, mode=1, start=True):
        """
        Enable and optionally start the Pixelblaze's internal sequencer. The mode parameters
        can be 1 - shuffle all patterns, or 2 - playlist mode.  The playlist
        must be configured through the Pixelblaze's web UI.
        """
        return await self._ws_send({"sequencerMode" : int(mode), "runSequencer" : start }, expect=["sequencerMode", "runSequencer"])
        
    async def stopSequencer(self):
        """Stop and disable the Pixelblaze's internal sequencer"""
        return await self.startSequencer(0, False)
        
    async def pauseSequencer(self):
        """
        Temporarily pause the Pixelblaze's internal sequencer, without
        losing your place in the shuffle or playlist. Call "playSequencer"
        to restart.  Has no effect if the sequencer is not currently running. 
        """
        return await self.runSequencer(False)
        
    async def playSequencer(self):
        """
        Start the Pixelblaze's internal sequencer in the current mode,
        at the current place in the shuffle or playlist.  Compliment to
        "pauseSequencer".  Will not start the sequencer if it has not
        been enabled via "startSequencer" or the Web UI.
        """
        return await self.runSequencer(True)
        
    async def runSequencer(self, run=True):
        '''
        stops or starts Pixelblaze's internal sequencer
        '''
        result =  await self._ws_send({"runSequencer" : self._str2bool(run) }, expect="runSequencer")
        return bool(result.get("runSequencer"))

    async def getControls(self, pattern=None):
        """
        Returns a dictionary containing the state of all the specified
        pattern's UI controls. If the pattern argument is not specified,
        returns the controls for the currently active pattern if available.
        Returns empty object if the pattern has no UI controls, None if
        the pattern id is not valid or is not available.
        (Note that getActivePattern() can return None on a freshly started
        Pixelblaze until the pattern has been explicitly set.)
        """
        # if pattern is not specified, attempt to get controls for active pattern
        # from hardware config
        if pattern is None:
            return await self._get_current_controls()

        # if pattern name or id was specified, attempt to validate against pattern list
        # and get stored values for that program
        pid = await self._get_pattern_id(pattern)
        if pid:
            ctl = await self._ws_send({"getControls": pid}, expect='controls')
            return {k:v for x in ctl.values() for k,v in x.items()} if ctl else {}
        return {}

    async def setControls(self, json_ctl, saveFlash=False):
        """
        Sets UI controls in the active pattern to values contained in
        the dictionary in argument json_ctl. To reduce wear on
        Pixelblaze's flash memory, the saveFlash parameter is ignored
        by default.  See documentation for _enable_flash_save() for
        more information.
        """
        save = self._get_save_value(saveFlash)
        result = await self._ws_send({"setControls": json_ctl, "save": save}, expect='ack')
        return bool(result)

    async def setControl(self, ctl_name, value, saveFlash=False):
        """
        Sets the value of a single UI controls in the active pattern.
        to values contained in in argument json_ctl. To reduce wear on
        Pixelblaze's flash memory, the saveFlash parameter is ignored
        by default.  See documentation for _enable_flash_save() for
        more information.
        """
        return await self.setControls({ctl_name: value}, saveFlash)

    async def setColorControl(self, ctl_name, color, saveFlash=False):
        """
        Sets the 3-element color of the specified HSV or RGB color picker.
        The color argument should contain an RGB or HSV color with all values
        in the range 0-1. To reduce wear on Pixelblaze's flash memory, the saveFlash parameter
        is ignored by default.  See documentation for _enable_flash_save() for
        more information.
        """

        # based on testing w/Pixelblaze, no run-time length or range validation is performed
        # on color. Pixelblaze ignores extra elements, sets unspecified elements to zero,
        # takes only the fractional part of elements outside the range 0-1, and
        # does something (1-(n % 1)) for negative elements.
        return await self.setControls({ctl_name: color}, saveFlash)

    async def controlExists(self, ctl_name, pattern=None):
        """
        Returns True if the specified control exists, False otherwise.
        The pattern argument takes the name or ID of the pattern to check.
        If pattern argument is not specified, checks the currently running pattern.
        Note that getActivePattern() can return None on a freshly started
        Pixelblaze until the pattern has been explicitly set.  This function
        also will return False if the active pattern is not available.
        """
        result = await self.getControls(pattern)
        return True if result and ctl_name in result.keys() else False

    async def getColorControlNames(self, pattern=None):
        """
        Returns a list of names of the specified pattern's rgbPicker or
        hsvPicker controls if any exist, None otherwise.  If the pattern
        argument is not specified, check the currently running pattern
        """
        controls = await self.getControls(pattern)
        if controls:
            self.log.debug('getControls: {}'.format(controls.keys()))
            return [key for key in controls.keys() if any([key.startswith("hsvPicker"), key.startswith("rgbPicker")])]
        return None

    async def getColorControlName(self, pattern=None):
        """
        Returns the name of the specified pattern's first rgbPicker or
        hsvPicker control if one exists, None otherwise.  If the pattern
        argument is not specified, checks in the currently running pattern
        """
        result = await self.getColorControlNames(pattern)
        return result[0] if result else None

    async def setDataspeed(self, speed, saveFlash=False):
        """
        Sets data rate for LEDs.
        CAUTION: For advanced users only.  If you don't know
        exactly why you want to do this, DON'T DO IT.
        
        See discussion in this thread on the Pixelblaze forum:
        https://forum.electromage.com/t/timing-of-a-cheap-strand/739
        
        Note that you must call _enable_flash_save() in order to use
        the saveFlash parameter to make your new timing (semi) permanent.
        """
        save = self._get_save_value(saveFlash)
        await self._ws_send({"dataSpeed":speed, "save":save})
        self._clear_cache()
        hw = await self.getHardwareConfig()
        return hw.get("dataSpeed")
        
    async def setpixelCount(self, num, saveFlash=False):
        """
        Sets number of pixels in strip
        
        Note that you must call _enable_flash_save() in order to use
        the saveFlash parameter to make your new timing (semi) permanent.
        """
        save = self._get_save_value(saveFlash)
        await self._ws_send({"pixelCount":num, "save":save})
        self._clear_cache()
        hw = await self.getHardwareConfig()
        return hw.get("pixelCount")
        
    async def getPreviewImg(self, pattern=None):
        """
        gets a preview (thumbnail) image in jpg format from pid or name
        """
        if not pattern:
            pid = await self.getActivePattern()   #current pattern ID
        else:
            pid = await self._get_pattern_id(pattern)
        result = await self._ws_send({"getPreviewImg" : pid }, binary=self.data_type['thumbnail_jpg'])
        result = result.replace(pid.encode('UTF-8'), b'')
        '''
        with open('test.jpg', 'wb') as f:
            f.write(result[loc:])
        '''
        return result
        
    async def getSources(self, pattern=None):
        """
        gets source text for PID or name (compressed as LZString Uint8Array)
        Currently not of much use.
        """
        if not pattern:
            pid = await self.getActivePattern()   #current pattern ID
        else:
            pid = await self._get_pattern_id(pattern)
        return await self._ws_send({"getSources" : pid }, binary=self.data_type['source_data'])
        
    async def getSourcesText(self, pattern=None):
        """
        gets source text for PID or name and uncomprsses it to plain text (for storing in .epe file)
        """
        if not pattern:
            pid = await self.getActivePattern()   #current pattern ID
        else:
            pid = await self._get_pattern_id(pattern)
        result = await self.getSources(pid)
        if result:
            return LZString.decompressFromUint8Array(result)
        return None
        
    async def getEPEFile(self, pattern=None, save=False):
        """
        returns epe file as json object sutiable for saving in a file
        from pid or name
        format is:
        {
          "name": "name of pattern as string",
          "id": "pid",
          "sources": {
            "main": "text of source file"
          },
          "preview": "binary preview image"
        }
        """
        epe = {}
        try:
            #if not pattern:
            #    pattern = await self.getActivePattern()   #current pattern ID
            pid, name = await self._get_pattern_id_and_name(pattern)
            if not all([pid, name]):
                self.log.warning('pattern{} Not found'.format(pattern))
                return None
            epe['name'] = name
            epe['id'] = pid
            sources = await self.getSourcesText(pid)
            if sources:
                epe['sources'] = json.loads(sources)
            preview = await self.getPreviewImg(pid)
            if preview:
                epe['preview'] = base64.b64encode(preview).decode('UTF-8')
            if save:
                fname = '{}.epe'.format(name)
                with open(name+'.epe', 'w') as f:
                    f.write(json.dumps(epe, indent=2))
                self.log.info('saved {} as file: {}'.format(pattern, fname))
            return epe
        except Exception as e:
            self.log.error(e)
            #self.log.exception(e)
        return None
        
    async def getUpgradeState(self):
        '''
        gets upgrade state
        returns True, False or None if state could not be retrieved
        '''
        result = await self._ws_send({"getUpgradeState" : True }, expect='upgradeState')
        return bool(result.get('code')) if result else None
        
    async def sendUpdates(self, on=False):
        '''
        sets updates on or off (preview, frame rate etc)
        '''
        await self._ws_send({"sendUpdates" : self._str2bool(on) })

    async def sendJson(self, arg):
        '''
        just send arg as a json command
        '''
        await self._ws_send(arg)


