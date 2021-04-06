# Pixelblaze-Async
A Python library that presents a simple, asynchronous interface for communicating with and
controlling one or more Pixelblaze LED controllers. Requires Python 3.6 and the aiohttp and paho-mqtt
modules.

**You need to be familiar with async programming and `asyncio` to use this as a library.**

You can, however just use it as a stand alone MQTT interface, it is self contained if used this way.  
See _Pixelblaze Usage_

Primarity intended for providing an MQTT interface to a Pixelblaze, MQTT support is built in.

Can also be used as a stand alone async client for pixelblaze devices, without MQTT support enabled.

The package to import is `pixelblaze_async`.

## Acknowledgements
Many thanks to JEM (ZRanger1) who was the inspiration for this library.  
See https://github.com/zranger1/pixelblaze-client for the original.

## Current Version: v1.0.0
Support for Pixelblaze's updated internal pattern sequencer.  

Support for starting the sequencer in either playlist or shuffle mode,
and pausing and unpausing.   See API docs for `startSequencer()`, `pauseSequencer()` and
`playSequencer()` below.

## Requirements
Python 3.6-3.8 (written and tested on 3.6.9)

* aiohttp (installable via pip, or from https://github.com/aio-libs/aiohttp )
* paho-mqtt (installable via pip) min version v1.5.0

## Known Issues
Having the web page open and using the Webocket at the same time can cause issues.
You will see a lot of updates if the web page is open (the web page gets preview frames from the websocket).  
The updates can be disabled on the web page - but I advise not running the websocket with the web page open.

## Installation
Clone this repository:
```
git clone https://github.com/NickWaterton/Pixelblaze-Async.git
cd Pixelblaze-Async
```
`Pixelblaze-Async` consists of several files:  
`PixelblazeClient`, `PixelblazeBase`, `PixelblazeEnumerator`, `LZString` and  `utils` in the `pixelblaze_async` directory from this repository.  
You can copy them into your project directory and use:
```
from PixelblazeClient import PixelblazeClient
from PixelblazeEnumerator import PixelblazeEnumerator
```
Depending on which class you want to use (or both). 
You can also install the module, by entering:
```
./setup.py install
```
from the top level dirrectory. This will install the modules as `pixelblaze_async`. You then import the modules using:
```
from pixelblaze_async.PixelblazeClient import PixelblazeClient
from pixelblaze_async.PixelblazeEnumerator import PixelblazeEnumerator
```
Sample code illustrating usage is provided in the [examples directory](https://github.com/NickWaterton/Pixelblaze-Async/blob/main/examples). 
The examples assume that the module has been installed or are in the same directory as the examples.

## Pixelblaze Usage
Just run `./pixelblaze.py` to see the options:
```
usage: pixelblaze.py [-h] [-t TOPIC] [-T FEEDBACK] [-b BROKER] [-p PORT]
                     [-U USER] [-P PASSWORD] [-poll POLL_INTERVAL] [-l LOG]
                     [-J] [-D] [--version]
                     pixelblaze_ip

Forward MQTT data to Pixelblaze controller

positional arguments:
  pixelblaze_ip         ipaddress of pixelblaze controller (default: None)

optional arguments:
  -h, --help            show this help message and exit
  -t TOPIC, --topic TOPIC
                        MQTT Topic to send commands to, (can use # and +)
                        default: /pixelblaze/command)
  -T FEEDBACK, --feedback FEEDBACK
                        Topic on broker to publish feedback to (default:
                        /pixelblaze/feedback)
  -b BROKER, --broker BROKER
                        ipaddress of MQTT broker (default: None)
  -p PORT, --port PORT  MQTT broker port number (default: 1883)
  -U USER, --user USER  MQTT broker user name (default: None)
  -P PASSWORD, --password PASSWORD
                        MQTT broker password (default: None)
  -poll POLL_INTERVAL, --poll_interval POLL_INTERVAL
                        Polling interval (0=off) (default: 0)
  -l LOG, --log LOG     path/name of log file (default: ./pixelblaze.log)
  -J, --json_out        publish topics as json (vs individual topics)
                        (default: True)
  -D, --debug           debug mode
  --version             Display version of this program
```

### How to use with MQTT
you should subscribe to the topic given in the constructor as `pubtopic` (eg `/pixelblaze/feedback/#`, or `/pixelblaze/feedback/Pixelblaze_F8BD97/#` for a single pixelblaze).
All updates will be posted to this base topic.  
The topic will be followed by the pixelblaze name (eg `Pixelblaze_F8BD97 `). Results of commands will also be followed by the command name. Genaral updates will have `update` at the end of the topic.

eg.
```
/pixelblaze/feedback/Pixelblaze_F8BD97/update {"name":"Pixelblaze_F8BD97","brandName":"","pixelCount":60,"brightness":1,"maxBrightness":100,"colorOrder":"BGR","dataSpeed":2000000,"ledType":1,"sequenceTimer":15,"sequencerMode":0,"runSequencer":false,"simpleUiMode":false,"discoveryEnable":true,"timezone":"America/Toronto","autoOffEnable":false,"autoOffStart":"00:00","autoOffEnd":"00:00","exp":0,"ver":"3.12"}
/pixelblaze/feedback/Pixelblaze_F8BD97/getHardwareConfig {"name":"Pixelblaze_F8BD97","brandName":"","pixelCount":60,"brightness":1,"maxBrightness":100,"colorOrder":"BGR","dataSpeed":2000000,"ledType":1,"sequenceTimer":15,"sequencerMode":0,"runSequencer":false,"simpleUiMode":false,"discoveryEnable":true,"timezone":"America/Toronto","autoOffEnable":false,"autoOffStart":"00:00","autoOffEnd":"00:00","exp":0,"ver":"3.12"}
```
To send a command, publish to the topic given in the constructor as `topic` followed by `all` for all pixelblases, or a specific name for just the one pixelblase
to respond (eg `/pixelblaze/command/all`, or `/pixelblaze/command/Pixelblaze_F8BD97`).  
There are two formats, with and without arguments

#### Examples:

##### With Arguments:
```
mosquitto_pub -h <broker_ip> -t "/pixelblaze/command/Pixelblaze_F8BD97/sendUpdates" -m False
mosquitto_pub -h <broker_ip> -t "/pixelblaze/command/Pixelblaze_F8BD97/setVariable" -m "r=0.5"
mosquitto_pub -h <broker_ip> -t "/pixelblaze/command/all/setActivePattern" -m "slow color shift"
mosquitto_pub -h 192.168.100.119 -t "/pixelblaze/command/all/setColorControl" -m "rgbPickerColor=(0.5,0,0)"
mosquitto_pub -h 192.168.100.119 -t "/pixelblaze/command/all/setColorControl" -m "rgbPickerColor=(0.5,0,0)=True"
```
if `rgbPickerColor` is the name of a colour control, `=True` will optionally save the value in flash (if `enable_flash_save()` has been called) . 
Note that arguments are seperated by `=` by default - eg (`g=0.3`, or `r=1.0`). This can be changed by setting `delimiter` to the string you want, this is a *regular expression* used in re.split.
Default is `'\='` (the `=` has to be escaped with a `\` as it's a special character in regular expressions). 

##### Without Arguments:
```
mosquitto_pub -h <broker_ip> -t "/pixelblaze/command/Pixelblaze_F8BD97" -m getHardwareConfig
mosquitto_pub -h <broker_ip> -t "/pixelblaze/command/all" -m getControls
```
Everything that is received is published to the base topic `/pixelblaze/feedback/<name>`, so if updates are on, you will receive updates like this:
```
/pixelblaze/feedback/Pixelblaze_F8BD97/update {"fps":903,"vmerr":0,"vmerrpc":-1,"mem":10239,"exp":0,"renderType":1,"uptime":21025663}
/pixelblaze/feedback/Pixelblaze_F8BD97/update {"fps":902,"vmerr":0,"vmerrpc":-1,"mem":10239,"exp":0,"renderType":1,"uptime":21026663}
/pixelblaze/feedback/Pixelblaze_F8BD97/update {"fps":902,"vmerr":0,"vmerrpc":-1,"mem":10239,"exp":0,"renderType":1,"uptime":21027664}
/pixelblaze/feedback/Pixelblaze_F8BD97/update {"fps":902,"vmerr":0,"vmerrpc":-1,"mem":10239,"exp":0,"renderType":1,"uptime":21028664}
```
If the command provides values, or feedback, the result is published to `<your feedbacktopic>/<pixelblaze name>/<command sent>` eg:
```
/pixelblaze/feedback/Pixelblaze_F8BD97/setColorControl True
/pixelblaze/feedback/Pixelblaze_F8BD97/getColorControlNames ['rgbPickerColor']
/pixelblaze/feedback/Pixelblaze_F8BD97/getColorControlName rgbPickerColor
/pixelblaze/feedback/Pixelblaze_F8BD97/waitForEmptyQueue True
```
If you subclass `PixelblazeClient()`, any method you define that does not start with `_` can be called from MQTT.  
see `GardenLEDController.py` in `examples` for how this works.

# Cache
By default the property `cache_timeout` is set to 5 seconds. `getHardwareConfig()`, `getPatternList()` results are cached for 5 seconds before being purged.  
This alows the use of commands that use these values without continually re-querying for these values.  
Commands that change these settings will automatically clear the cache first.
Cache can be disabled by setting this property to 0.

# API Documentation
Roughly alphabetical except for object constructors.

## class PixelblazeEnumerator
Asyncronous Discovery class for pixelblaze
### PixelblazeEnumerator(addr='0.0.0.0', log=None)
Create an object that listens continuously for Pixelblaze time and beacon
packets, and maintains a list of visible Pixelblazes.  The PixelblazeEnumerator
object also supports synchronizing time on multiple Pixelblazes to allows
them to run patterns simultaneously.

Takes the IPv4 address of the interface to use for listening on the calling computer.
Listens on all available interfaces if addr is not specified.

log is optional if you want to pass a python logging object

See `auto_pixelblaze.py` in `examples` for an example of usage.
### Async Methods
The following need to be awaited
#### Start()
Must be called to start listening for pixelblaze devices. Should only be called once.
example:
```
loop = asyncio.get_event_loop()
pb_enum = PixelblazeEnumerator()

try:
    asyncio.gather(pb_enum.start(), return_exceptions=True)
    loop.run_forever()
        
except (KeyboardInterrupt, SystemExit):
    pb_enum.stop()
```
### Syncronous API
The below are all syncronous methods.
#### stop()
Stops the discovery class.

#### disableTimesync()
Turns off the time synchronization -- the PixelblazeEnumerator will not
automatically synchronize Pixelblazes. 

#### enableTimesync()
Instructs the PixelblazeEnumerator object to automatically synchronize
time on all Pixelblazes. (Note that time synchronization
is off by default when a new PixelblazeEnumerator is created.)
 
#### getPixelblazeList()
Returns a list of Pixelblazes (ip addresses) visible on the network.

#### setDeviceTimeout(s)
Sets the interval in milliseconds which the enumerator will wait without
hearing from a Pixelblaze before removing it from the active devices list.        
The default timeout is 30 (30 seconds).

#### devices
A Dictionary containing all discovered pixelblaze devices, key is the device id.
```
{ id:   "address"    : ip_addr,
        "timestamp"  : received time,
        "sender_id"  : id,
        "sender_time": timestamp}
```
**NOTE this is a propety, not a method.**

## class PixelblazeClient
Asyncronous Class for interfaceing with pixelblaze devices, has integrated MQTT control.
You should instantiate one class instance per pixelblaze device.
### PixelblazeClient(pixelblase_ip, user, password, broker, port, topic, pubtopic, json_out, timeout, poll, log)
Create Pixelblaze object. Takes the Pixelblaze's IPv4 address in the usual 12 digit numeric form (for example, `192.168.1.xxx`)  Returns a Pixelblaze object. To control multiple Pixelblazes, create multiple objects.

Constructor:
```
PixelblazeClient(  pixelblase_ip=None,
                   user=None,
                   password=None,
                   broker=None,
                   port=1883,
                   topic='/pixelblaze/command',
                   pubtopic='/pixelblaze/feedback',
                   json_out=True,
                   timeout=30.0,
                   poll=0,
                   log=None)
```
### Async Methods
The following all need to be awaited

### Class control methods

#### start()
Starts the websocket connection. Not called automatically
when a Pixelblaze object is created - it is necessary to
explicitly call `start()` to start the interface.  
eg:
```
asyncio.gather(pb.start(), return_exceptions=True)
loop.run_forever()
```
This should only be called once.
Websocket will automatically reconnect if the connection drops for some reason.

#### start_ws()
Alternative start function. Starts the websocket, but waits for it to connect, and for pixelblaze name to be found.  
Useful in programs where you want to wait for the connection and name to be established before proceeding.  
See examples for usage.

#### _stop()
See Syncronous method `stop()`.
Stops all processes, and closes the websocket. Can (should) be used at the end of your program.
Connection can be restarted using `start()` again.

#### connect()
Connects the websocket (if not already connected), can be used if you have run `disconnect()`.  
Websocket will automatically reconnect if the connection drops for some reason.
Must run `start()` first.

#### diconnect()
Disconnects the websocket, if you don't want to leave it connected.  
Don't forget to run `connect()` before issuing any commands!

### MQTT accessible API calls

#### controlExists(ctl_name, pattern=None)
Returns `True` if the specified control exists, `False` otherwise.
The pattern argument takes the name or ID of the pattern to check.
If pattern argument is not specified, checks the currently running pattern.
Note that this can return `False` on a freshly started pixelblaze, until the active pattern has been set.  
This function also will return `False` if the active pattern is not available.

#### deletePattern(pattern):
Deletes the pattern given by pattern (pid or name).  
Note: if you delete the active pattern, it will continue to run, 
it will just be deleted from the list of available patterns.

#### getActivePattern()
Returns the ID of the pattern currently running on
the Pixelblaze if available.  Otherwise returns an empty dictionary
object

#### getActivePatternName()
Returns the Name of the pattern currently running on
the Pixelblaze if available.  Otherwise returns an empty dictionary
object

#### getBrightness():
Returns current global brightness (0-1), or `None` if not available.

#### getColorControlName(pattern=None)
Returns the name of the specified pattern's first `rgbPicker` or `hsvPicker` control
if it exists, `None` otherwise.  If the pattern argument is not specified,
checks in the currently running pattern.

#### getColorControlNames(pattern=None)
Returns a list of the names of the specified pattern's `rgbPicker` or
`hsvPicker` controls if any exist, None otherwise.  If the pattern
argument is not specified, check the currently running pattern

#### getControls(pattern=None)
Returns a dictionary containing the state of all the specified
pattern's UI controls. If the pattern argument is not specified,
returns the controls for the currently active pattern if available.
Returns empty dictionary if the pattern has no UI controls, `None` if
the pattern id is not valid or is not available.
(Note that `_get_current_controls()` can return `None` on a freshly started
Pixelblaze until the pattern has been explicitly set.)

#### getEPEFile(pattern=None, save=False)
Returns epe file as a dictionary sutiable for saving in a file from pid or name.  
If `save` is `True` saves the file as an `.epe` file in the current directory with the pattern name.
Will return `None` if the pattern is not found.

#### getHardwareConfig()
Returns a dictionary containing all the available hardware configuration data

#### getIP()
Returns the ip for the connected pixelblaze.

#### getPatternList()
Returns a dictionary containing the unique ID and the text name of all
saved patterns on the Pixelblaze

#### getPreviewImg(pattern)
Gets a preview (thumbnail) image in jpg format from PID or name.  
Returns the jpeg binary data or `None`.

#### getSources(pattern)
Gets source text for PID or name (compressed as LZString Uint8Array).  
Currently not of much use.  
**This is not the same data as returned by `save_binary_file()`**  
Returns the binary data or `None`.

#### getSourcesText(pattern=None)
Gets source text for PID or name and uncomprsses it to plain text (for storing in .epe file).  
Returns the plain text of the pattern or `None`.

#### getUpgradeState()
returns `True` or `False` if an upgrade is available, `None` if state could not be retrieved

#### getVars()
Returns a dictionary containing all vars exported from the active pattern

#### getWSConnected()
Returns `True` or `False` if websocket is connected or not.

#### load_binary_file(filename=None, binary=None)
Loads the binary data passed to `binary` as a pattern file. `filename` should be the PID the file will be loaded as. 
The binary data is in the format received from `save_binary_file()`.  
You can use this command to clone patterns from one pixelblaze to another.
if `binary` is not given, then the current directory will be searched for a file `filename.bin`, if that is not
found, then all `.bin` files will be searched for the string `filename` which should be a pattern name.  
If a file is found, it is loaded to the pixelblaze, using the found filename as the PID (excluding the `.bin`).  
**This is not for loading `.epe` files**  
Returns either the PID loaded from the file, or `None` if not found.
See `save_load_pattern.py` for an example use.

#### pauseSequencer()
Temporarily pause the Pixelblaze's internal sequencer, without
losing your place in the shuffle or playlist. Call `playSequencer()`
to restart.  Has no effect if the sequencer is not currently running. 
Returns the current sequencer state `True` (running) or `False`.
        
#### playSequencer()
Starts the Pixelblaze's internal sequencer in the current mode,
at the current place in the shuffle or playlist.  Will not start the sequencer if it has not
been enabled via `startSequencer()` or the Web UI.  
Returns the current sequencer state `True` (running) or `False`.

#### read_binary_file(filename=None, binary_only=False)
loads a binary file (`.bin`) and returns the PID and binary data (as bytes).  
If the filename is not found, searches the current directory using `filename` as the pattern name.  
Returns pid, binary_data, or `None`, `None`.  
if `binary_only` is set, just returns binary data or `None`

#### runSequencer(run=True)
Stops or starts the Pixelblaze's internal sequencer in the current mode,
at the current place in the shuffle or playlist.  Will not start the sequencer if it has not
been enabled via `startSequencer()` or the Web UI.  
Returns the current sequencer state `True` (running) or `False`.

#### save_binary_file(pattern=None, save=False)
Downloads the given pattern (pid or name), and returns the binary data, optionally, saves it as a binary file. 
Uses `pid.bin` as the filename if saved to a file. 
Returns the binary data, or `None`.
See `save_load_pattern.py` for an example use.

#### sendJson(arg)
Sends arg (dictionary) as a json command, so you can build your own sequence of commands.  
There is no checking performed.  
Returns `None`.

#### sendUpdates(on=False)
Sets updates on or off (preview, frame rate etc).  
Returns `None`.

#### setActivePattern(pid, saveFlash=False)
Sets the currently running pattern, using either an ID or a text name.  
To reduce wear on Pixelblaze's flash memory, the saveFlash parameter
is ignored by default.  See documentation for `_enable_flash_save()` for
more information.  
Returns `True` if the active pattern was set successfuly, `False` if not, or `None` if the pattern was not found. 

#### setActivePatternId(pid, saveFlash=False):
Sets the active pattern by pattern ID, without the name lookup option
supported by `setActivePattern()`. This method is faster and more network efficient than `SetActivePattern()`
if you already know a pattern's ID. It does not validate the input id, or determine if the pattern is
 available on the Pixelblaze.  
To reduce wear on Pixelblaze's flash memory, the saveFlash parameter
is ignored by default.  See documentation for `_enable_flash_save()` for
more information.  
 Returns `True` if the active pattern was set successfuly, `False` otherwise.

#### setBrightness(n, saveFlash=False)
Set the Pixelblaze's global brightness(%).  Valid range is 0-100. 
To reduce wear on Pixelblaze's flash memory, the saveFlash parameter
is ignored by default.  See documentation for `_enable_flash_save()` for
more information.  
Returns `None`.

#### setMaxBrightness(n, saveFlash=False)
Set the Pixelblaze's global Maximum brightness.  Valid range is 0-1. 
To reduce wear on Pixelblaze's flash memory, the saveFlash parameter
is ignored by default.  See documentation for `_enable_flash_save()` for
more information.  
Returns `None`.

#### setColorControl(ctl_name, color, saveFlash=False)
Sets the 3-element color of the specified HSV or RGB color picker.
The color argument should contain an RGB or HSV color with all values
in the range 0-1. To reduce wear on Pixelblaze's flash memory, the saveFlash parameter
is ignored by default.  See documentation for `_enable_flash_save()` for
more information.  
        
Based on testing w/Pixelblaze, no run-time length or range validation is performed
on color. Pixelblaze ignores extra elements, sets unspecified elements to zero,
takes only the fractional part of elements outside the range 0-1, and
does something like `(1-(n % 1))` for any negative elements.
returns `True` or `False` if the control was set.

#### setControl(ctl_name, value, saveFlash=False)
Sets the value of a single UI controls in the active pattern.
to values contained in the argument json_ctl. To reduce wear on Pixelblaze's flash memory, the saveFlash parameter is ignored
by default.  See documentation for `_enable_flash_save()` for
more information.  
returns `True` or `False` if the control was set.

#### setControls(json_ctl, saveFlash=False)
Sets UI controls in the active pattern to values contained in
the dictionary in argument json_ctl. To reduce wear on
Pixelblaze's flash memory, the saveFlash parameter is ignored
by default.  See documentation for `_enable_flash_save()` for
more information.
returns `True` or `False` if the control was set.

#### setcolorOrder(order, saveFlash=False):
Sets colur order in strip, "BGR", "RGB" etc.
Note that you must call _enable_flash_save() in order to use
the saveFlash parameter to make your new timing (semi) permanent.

#### setDataspeed(speed, saveFlash=False)
Sets data speed for all types of LEDs.  
**CAUTION:** For advanced users only.  If you don't know
exactly why you want to do this, DON'T DO IT.

Note that you must call `_enable_flash_save()` (sync) or `enable_flash_save()` (async version) in order to use
the saveFlash parameter to make your new timing (semi) permanent.
Returns the current datasepeed.

#### setIP(ip=None)
if ip is given, sets the pixelblaze ip you are connected to. Restarts websocket with new ip.
Returns the ip of the pixelblaze you are connected to

#### setName(name)
Sets the pixelblaze name (permenantly).
if MQTT is in use, will unsubscribe from the old name topic, and subscribe to the new one
Returns the new name.

#### setpixelCount(num, saveFlash=False)
Sets number of pixels in strip.  
returns the current number of pixels.

#### setSequenceTimer(n)
Sets number of milliseconds the Pixelblaze's sequencer will run each pattern
before switching to the next.  
returns `None`.

#### startSequencer(mode=1)
Enable and start the Pixelblaze's internal sequencer. The optional mode parameter
can be:  
1. - shuffle all patterns 
2. - playlist mode
The playlistmust be configured through the Pixelblaze's web UI.  
Returns the current sequencer mode.

#### stopSequencer()
Stop and disable the Pixelblaze's internal sequencer.  
Returns the current sequencer mode.

#### setVariable(var_name, value)
Sets a single variable to the specified value. Does not check to see if the
variable is actually exported by the current active pattern.  
Returns the value of the variable set, or `None` if the variable does not exist.

#### setVars(json_vars)
Sets pattern variables contained in the json_vars (dictionary) argument.
Does not check to see if the variables are exported by the current active pattern.  
Returns `None`

#### variableExists(var_name)
Returns `True` if the specified variable exists in the active pattern, `False` otherwise.

#### waitForEmptyQueue(timeout_ms=1000):
Wait until the Pixelblaze's websocket message queue is empty, or until
timeout_ms milliseconds have elapsed.  Returns True if an empty queue
acknowldgement was received, False if timeout or error occurs.

### Utility methods (available from MQTT)

#### enable_flash_save()
Async version of `enable_flash_save()`, see below.

### Utility methods (not available from MQTT)

#### _clear_cache()
Clears the cache.

#### _find_pattern_file(name)`
Finds the binary file in the current directory (ends with `.bin`) for pattern name.  
returns the filename or `None`.

#### _get_active_pattern()
Returns the ID of the pattern currently running on the Pixelblaze if available.  
Otherwise returns an empty dictionary.

#### _get_current_controls()
Utility Method: Returns controls for currently running pattern if available, `None` otherwise

#### _get_hardware_config()
Returns a dictionary containing all the available hardware configuration data.

#### _get_pattern_id(pattern)
Utility Method: Returns a pattern ID if passed either a valid ID or a text name.

#### _get_pattern_id_and_name(pattern)
Utility Method: Returns a pattern ID and name if passed either a valid ID or a text name.
returns `pid, name`.

#### _get_patterns()
Returns patterns dictionary

#### _waitForMQTT()
Wait for MQTT broker to be connected

#### _waitForWS()
Wait for websocket to connect

## Syncronous API
The below are all syncronous methods.

### Utility methods (not available from MQTT)

#### _enable_flash_save(enable=False)
**IMPORTANT SAFETY TIP:**
To preserve your Pixelblaze's flash memory, which can wear out after a number of
cycles, you must call this method before using setControls() with the
saveFlash parameter set to True.
If this method is not called, setControls() will ignore the saveFlash parameter
and will not save settings to flash memory.
You can unset the value by calling `_enable_flash_save(False)

#### __find_pattern_file(pattern_name)
syncronous version of `_find_pattern_file`

#### _id_from_name(patterns, name)
Utility method: Given the list of patterns and text name of a pattern, returns that pattern's ID.

#### _MQTT_connected
property that equals `True` or `False` if the MQTT broker is connected or not.  
**NOTE: This is a property, not a method**

#### _name_from_id(patterns, pid)
Utility method: Given the list of patterns and pid of a pattern, returns that pattern's Name.

#### _get_active_pattern(name=False)
Returns the Name or ID of the pattern currently running on
the Pixelblaze if available depending on whether `name` is true or not.  
Otherwise returns an empty dictionary object

#### _get_pattern_id(pid)
Returns a pattern ID if passed either a valid ID or a text name

#### subscribe(topic, qos=0)
Subscribes to the topic (appended to the base topic passed in the class constructor)

#### unsubscribe(topic)
UnSsubscribes from the topic (appended to the base topic passed in the class constructor)



