#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
GardenLEDController.py

Pixelblaze based LED controller for APA102/SK9822 LED Strips
Working Example

N Waterton V 1.0 16th March 2021: Initial release
'''
 
__version__ = "1.0.1"

import sys
import logging
import asyncio

try:
    from pixelblaze_async.PixelblazeClient import PixelblazeClient
    from pixelblaze_async.PixelblazeEnumerator import PixelblazeEnumerator
except (ImportError, ModuleNotFoundError):
    from PixelblazeClient import PixelblazeClient
    from PixelblazeEnumerator import PixelblazeEnumerator
    
class LEDController(PixelblazeClient):
    '''
    LEDController based on PixelblazeClient for Garden LED Lights
    Add methods based on specific commands you want to use
    '''
    
    __version__ = "1.0.1"
    
    modes = {2: 'Slave to Controller',  #blank mode
             3: 'Rainbow',
             5: 'Fade 7',
             8: 'Fade HSI',
             9: 'Rainbow',              #duplicate
             11: 'Canada Day'
            }

    def __init__(self, pixelblaze_ip=None,
                       user=None,
                       password=None,
                       broker='localhost',
                       port=1883,
                       topic='/pixelblaze/command',
                       pubtopic='/pixelblaze/feedback',
                       json_out=True,
                       timeout=30.0,
                       poll=0,
                       log=None):
                       
        super().__init__(pixelblaze_ip,
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
                         
        self.mode = None            #current mode number
        self.publish_name = False   #do not publish pb name in topics
        self.saved_values = {}
                       
    async def primary_rgb(self, r, g, b):
        '''
        set rgb strip values in slave mode
        '''
        if self.mode == 2:
            rgb_dict = {"r": float(r)/255.0,"g": float(g)/255.0, "b": float(b)/255.0}
            await self.setVars(rgb_dict)
        else:
            self.log.info('ignoring primary_rgb command - not in mode 2')
    
    #override brightness
    async def brightness(self, val):
        '''
        set master brightness from LED Controller command
        '''
        #convert int 0-31 to float 0-1
        await self.setBrightness(float(val)/31.0)
        
    async def max_brightness_percent(self, val):
        self.saved_values['max_brightness_percent'] = val
        if self.mode != 2:
            result = await self.setVariable('max_brightness', float(val)/100)
            return result*100 if result is not None else None
        
    async def min_brightness_percent(self, val):
        self.saved_values['min_brightness_percent'] = val
        if self.mode != 2:
            result = await self.setVariable('min_brightness', float(val)/100)
            return result*100 if result is not None else None
        
    async def fps_percent(self, val):
        self.saved_values['fps_percent'] = val
        if self.mode != 2:
            result = await self.setVariable('fps', float(val)/100)
            return result*100 if result is not None else None
        
    async def hue_increment_percent(self, val):
        self.saved_values['hue_increment_percent'] = val
        if self.mode != 2:
            result = await self.setVariable('hue_increment', float(val)/100)
            return result*100 if result is not None else None
        
    async def saturation_percent(self, val):
        self.saved_values['saturation_percent'] = val
        if self.mode != 2:
            result = await self.setVariable('saturation', float(val)/100)
            return result*100 if result is not None else None
        
    async def pathlight_percent(self, val):
        if self.mode != 2:
            result = await self.setVariable('pathlight', float(val)/100)
            return result*100 if result is not None else None
        
    async def red_percent(self, val):
        result = True if self.mode == 2 else await self.display_mode(2)
        if result:
            result = await self.setVariable('r', float(val)/100)
            return result*100 if result is not None else None
        
    async def green_percent(self, val):
        result = True if self.mode == 2 else await self.display_mode(2)
        if result:
            result = await self.setVariable('g', float(val)/100)
            return result*100 if result is not None else None
        
    async def blue_percent(self, val):
        result = True if self.mode == 2 else await self.display_mode(2)
        if result:
            result = await self.setVariable('b', float(val)/100)
            return result*100 if result is not None else None
        
    async def set_all_percent(self, val):
        result = True if self.mode == 2 else await self.display_mode(2)
        if result:
            result = await primary_rgb(val, val, val)
            return result*100 if result is not None else None
        
    async def relay_on(self):
        return await self.setVariable('relay', True)
        
    async def relay_off(self):
        return await self.setVariable('relay', False)
        
    async def display_mode(self, mode=2):
        '''
        set pattern to run
        '''
        name = self.modes.get(mode, 'Slave to Controller')
        self.log.info('setting active pattern to: {}'.format(name))
        result = await self.setActivePattern(name)
        if not result:
            self.log.warning('pattern not found on PB')
            filename = await self._find_pattern_file(name)
            if filename:
                if await self.load_binary_file(filename):
                    result = await self.setActivePattern(name)
        if result:
            self.mode = mode
            if mode == 2:
                await self.primary_rgb(0,0,0)
            else:
                #restore saved settings
                for k, v in self.saved_values.items():
                    if k in self.method_dict.keys():
                        await self.method_dict[k](v)
        return mode if result else None
        
    async def _LEDStrip_start(self):
        '''
        setup Pixelblase for my LED strip Control
        '''
        try:
            #change delimiter, as this receives messages of the form r,g,b eg 128,64,255
            #in slave mode.
            #this means normal commands with arguments won't work
            self.delimiter=','
            await self.start_ws()
            #set log
            self.log = logging.getLogger("Pixelblaze.{}.{}".format(__class__.__name__, self.name))
            #subscribe to topics (this application uses an existing topic scheme)
            #wait for MQTT connection
            if await self._waitForMQTT():
                #subscribe to base topic (no pb name needed) for commands (other than in mode 2)
                #self.subscribe('{}/#'.format(self.topic))
                #subscribe to slave mode topic for receiving rgb values in mode 2
                self.subscribe('{}/primary_rgb'.format(self.pubtopic))
            self.log.info('Set Active pattern')
            #set to slave mode on start up
            if await self.display_mode(2):
                self.log.info('Active pattern Set correctly')   
            else:
                self.log.warning('Active pattern could not be set correctly')
                
            #anything else you want here
            
                
        except asyncio.CancelledError:
            pass
            
class PixelblazeFinder(PixelblazeEnumerator):

    def __init__(self, arg, hostIP="0.0.0.0", log=None):
        super().__init__(hostIP, log)
        self.arg = arg
        self.connections = {}
        
    #override _disconnect        
    async def _disconnect(self):
        for pb in self.connections.values():
            await pb._stop()
        await super()._disconnect()
        
    async def _LEDStrip_start(self):
        '''
        start LED strip discovery
        '''
        self.log.info('Starting LED Strip Enumerator')
        self.enableTimesync()
        self.loop.create_task(self.discovery())
        await self.start()
            
    async def discovery(self):
        '''
        finds and connect/disconnect pixelblaze controllers
        '''
        self.log.info('Starting Pixelblaze discovery')
        while not self._exit:
            try:
                #add new pb
                for ip in [v["address"][0] for v in self.devices.values()]:
                    if ip not in self.connections.keys():
                        self.log.info('Adding pb: {}'.format(ip))
                        self.connections[ip] = LEDController(ip, self.arg.user, self.arg.password, self.arg.broker, self.arg.port, self.arg.topic, self.arg.feedback, self.arg.json_out, poll=self.arg.poll_interval)
                        await self.connections[ip]._LEDStrip_start()
                        
                #remove old pb        
                for ip, pb in self.connections.copy().items():
                    if ip not in [v["address"][0] for v in self.devices.values()]:
                        self.log.info('Removing pb: {}'.format(ip))
                        await pb._stop()    #note do NOT use pb.stop() here
                        del self.connections[ip]
                               
                await asyncio.sleep(self.LIST_CHECK_INTERVAL)
                        
            except asyncio.CancelledError:
                break
        self.log.info('Exit Pixelblaze discovery')              
    
def main():
    from pixelblaze_async.utils import parse_args, setup_logger
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
    
    if arg.pixelblaze_ip:
        pbs = [LEDController(ip, arg.user, arg.password, arg.broker, arg.port, arg.topic, arg.feedback, arg.json_out, poll=arg.poll_interval) for ip in arg.pixelblaze_ip]
    else:
        pbs = [PixelblazeFinder(arg)]
    
    try:
        #asyncio.gather(*[pb._LEDStrip_start(), pb_enum.start()])
        asyncio.gather(*[pb._LEDStrip_start() for pb in pbs], return_exceptions=True)    #uncomment if you don't want to run pb_enum
        loop.run_forever()
            
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
        for pb in pbs:
            pb.stop()
        
    finally:
        pass
        
if __name__ == '__main__':
    main()