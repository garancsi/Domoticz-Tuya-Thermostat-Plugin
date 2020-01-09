########################################################################################
#     Domoticz Tuya Smart Plug Python Plugin                                              #
#                                                                                      #
#     MIT License                                                                        #
#                                                                                      #
#    Copyright (c) 2018 tixi                                                            #
#                                                                                      #
#    Permission is hereby granted, free of charge, to any person obtaining a copy       #
#    of this software and associated documentation files (the "Software"), to deal      #
#    in the Software without restriction, including without limitation the rights       #
#    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell          #
#    copies of the Software, and to permit persons to whom the Software is              #
#    furnished to do so, subject to the following conditions:                           #
#                                                                                      #
#    The above copyright notice and this permission notice shall be included in all     #
#    copies or substantial portions of the Software.                                    #
#                                                                                      #
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR         #
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,           #
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE        #
#    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER             #
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,      #
#    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE      #
#    SOFTWARE.                                                                          #
#                                                                                      #
########################################################################################


"""
<plugin key="iasmanis_tuya_thermostat_plugin" name="Tuya Thermostat" author="iasmanis" version="3.0.0" externallink="https://github.com/iasmanis/Domoticz-Tuya-Thermostat-Plugin">
    <params>
        <param field="Address" label="IP address" width="200px" required="True"/>
        <param field="Mode1" label="DevID" width="200px" required="True"/>
        <param field="Mode2" label="Local Key" width="200px" required="True"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="False"   value="0" default="True"/>
                <option label="True"   value="1"/>
            </options>
        </param>
    </params>
</plugin>
"""

# https://wiki.domoticz.com/wiki/Developing_a_Python_plugin
# Debugging
# Value     Meaning
# 0         None. All Python and framework debugging is disabled.
# 1         All. Very verbose log from plugin framework and plugin debug messages.
# 2         Mask value. Shows messages from Plugin Domoticz.Debug() calls only.
# 4         Mask Value. Shows high level framework messages only about major the plugin.
# 8         Mask Value. Shows plugin framework debug messages related to Devices objects.
# 16         Mask Value. Shows plugin framework debug messages related to Connections objects.
# 32         Mask Value. Shows plugin framework debug messages related to Images objects.
# 64         Mask Value. Dumps contents of inbound and outbound data from Connection objects.
# 128         Mask Value. Shows plugin framework debug messages related to the message queue.

import Domoticz
import pytuya
import json
import math

########################################################################################
#
# plugin object
#
########################################################################################


class BasePlugin:

    #######################################################################
    #
    # constant definition
    #
    #######################################################################
    __HB_BASE_FREQ = 2  # heartbeat frequency (val x 10 seconds)

    #######################################################################
    #
    # __update_status
    #
    # Parameter
    #    Data: a received payload from the tuya smart plug
    #
    # Returns a tuple (bool,dict)
    #    first:  set to True if an error occur and False otherwise
    #    second: dict of the dps (irrelevant if first is True )
    #
    #######################################################################
    def __update_status(self, Data):

        start = Data.find(b'{"devId')

        if(start == -1):
            # Domoticz.Error("Invalid payload received: " + str(Data))
            Domoticz.Debug("Got non dps response: " +
                           str(Data) + ", probably set response")
            return

        jsonstr = Data[start:]

        end = jsonstr.find(b'}}')

        if(end == -1):
            Domoticz.Error("Invalid payload received: " + str(Data))
            return

        end = end+2
        jsonstr = jsonstr[:end]

        try:
            result = json.loads(jsonstr)
            Domoticz.Debug("Loaded: " + str(result['dps']))
        except (JSONError, KeyError) as e:
            Domoticz.Error("Payload parse failed: " + jsonstr)
            return

        if result['devId'] != self.__devID:
            Domoticz.Error("Invalid payload received for " + result['devId'])
            return

        if ((type(result['dps']) is dict) == False):
            Domoticz.Error("Invalid dps block: " + jsonstr)
            return

        try:
            if result['dps']['1']:
                UpdateDevice(self.__control_device, 1, "On")
            else:
                UpdateDevice(self.__control_device, 0, "Off")
        except KeyError:
            pass

        try:
            current_temp = str(round(result['dps']['2']/2, 1))
            # TODO check which value shoud be set
            UpdateDevice(self.__thermostat_device, 0, current_temp)
        except KeyError:
            pass

        try:
            if result['dps']['4'] == "1":
                UpdateDevice(self.__mode_device, 10, "10")
            else:
                UpdateDevice(self.__mode_device, 20, "20")
        except KeyError:
            pass

        try:
            if result['dps']['6']:
                UpdateDevice(self.__lock_device, 20, "20")
            else:
                UpdateDevice(self.__lock_device, 10, "10")
        except KeyError:
            pass

        try:
            if result['dps']['5']:
                UpdateDevice(self.__eco_device, 20, "20")
            else:
                UpdateDevice(self.__eco_device, 10, "10")
        except KeyError:
            pass

        # builtin sensor reading
        try:
            current_temp = str(round(result['dps']['3']/2, 1))
            UpdateDevice(self.__temp_device, 0, current_temp)
        except KeyError:
            pass

        # External sensor present
        try:
            current_temp = str(round(result['dps']['102']/2, 1))
            UpdateDevice(self.__external_temp_device, 0, current_temp)
        except KeyError:
            pass

    #######################################################################
    #
    # __request_status
    #    request status from tuya device
    #
    #
    #######################################################################

    def __request_status(self):

        self.__runAgain = self.__HB_BASE_FREQ

        if(self.__connection.Connected()):
            self.__state_machine = 2
            payload = self.__device.generate_payload('status')
            self.__connection.Send(payload)

        else:
            if(not self.__connection.Connecting()):
                self.__connection.Connect()

    #######################################################################
    #
    # __send_update
    #    send a command to the tuya device
    #
    #
    #######################################################################
    def __send_update(self, dps, value):

        if(self.__connection.Connected()):
            self.__state_machine = 1
            dict_payload = {str(dps): value}

            Domoticz.Debug("__send_update dict: " + str(dict_payload))
            payload = self.__device.generate_payload('set', dict_payload)
            Domoticz.Debug("__send_update payload: " + str(payload))
            self.__connection.Send(payload)

    #######################################################################
    #
    # constructor
    #
    #######################################################################
    def __init__(self):
        self.__address = None  # IP address of the Thermostat
        self.__devID = None  # devID of the Thermostat
        self.__localKey = None  # localKey of the Thermostat
        self.__device = None  # pytuya object of the Thermostat
        self.__runAgain = self.__HB_BASE_FREQ  # heartbeat frequency
        self.__connection = None  # connection to the tuya plug
        # domotics control ID (On/Off switch)
        self.__control_device = 1
        self.__thermostat_device = 2
        self.__mode_device = 3
        self.__lock_device = 4
        self.__eco_device = 5
        self.__temp_device = 6
        self.__external_temp_device = 7
        # state_machine: 0 -> no waiting msg ; 1 -> set command sent ; 2 -> status command sent
        self.__state_machine = 0
        return

    #######################################################################
    #
    # onStart Domoticz function
    #
    #######################################################################
    def onStart(self):

        # Debug mode
        Domoticz.Debugging(int(Parameters["Mode6"]))
        Domoticz.Debug("onStart called")

        # get parameters
        self.__address = Parameters["Address"]
        self.__devID = Parameters["Mode1"]
        self.__localKey = Parameters["Mode2"]

        # set the next heartbeat
        self.__runAgain = self.__HB_BASE_FREQ

        # build internal maps (__control_device and __domoticz_controls)

        self.__domoticz_controls = {}

        # create domoticz devices
        if(len(Devices) == 0):

            Domoticz.Device(Name="Thermostat Control",
                            Unit=self.__control_device,
                            Image=15,
                            TypeName="Switch",
                            Used=1).Create()

            Domoticz.Log("Tuya Thermostat Control created.")

            Domoticz.Device(Name="Thermostat Setpoint",
                            Unit=self.__thermostat_device,
                            Image=15,
                            Type=242,
                            Subtype=1,
                            Used=1).Create()

            Domoticz.Log("Thermostat Setpoint created.")

            ModeOptions = {"LevelActions": "|||",
                           "LevelNames": "Off|Manual|Schedule",
                           "LevelOffHidden": "True",
                           "SelectorStyle": "0"}

            Domoticz.Device(Name="Thermostat Mode",
                            Unit=self.__mode_device,
                            Image=15,
                            TypeName="Selector Switch",
                            Switchtype=18,
                            Options=ModeOptions).Create()

            LockOptions = {"LevelActions": "|||",
                           "LevelNames": "Off|Unlocked|Locked",
                           "LevelOffHidden": "True",
                           "SelectorStyle": "0"}

            Domoticz.Device(Name="Thermostat Lock",
                            Unit=self.__lock_device,
                            Image=15,
                            TypeName="Selector Switch",
                            Switchtype=18,
                            Options=LockOptions).Create()

            EcoOptions = {"LevelActions": "|||",
                          "LevelNames": "Off|Normal|Eco",
                          "LevelOffHidden": "True",
                          "SelectorStyle": "0"}

            Domoticz.Device(Name="Thermostat Eco",
                            Unit=self.__eco_device,
                            Image=15,
                            TypeName="Selector Switch",
                            Switchtype=18,
                            Options=EcoOptions).Create()

            Domoticz.Device(Name="Temperature",
                            Unit=self.__temp_device,
                            Image=15,
                            TypeName="Temperature",
                            Used=1).Create()

            Domoticz.Device(Name="Floor Temperature",
                            Unit=self.__external_temp_device,
                            Image=15,
                            TypeName="Temperature",
                            Used=0).Create()

        # create the pytuya object
        self.__device = pytuya.OutletDevice(
            self.__devID, self.__address, self.__localKey)

        # state machine
        self.__state_machine = 0

        # start the connection
        self.__connection = Domoticz.Connection(
            Name="Tuya", Transport="TCP/IP", Address=self.__address, Port="6668")
        self.__connection.Connect()

    #######################################################################
    #
    # onConnect Domoticz function
    #
    #######################################################################
    def onConnect(self, Connection, Status, Description):
        if (Connection == self.__connection):
            if (Status == 0):
                Domoticz.Debug("Connected successfully to: " +
                               Connection.Address+":"+Connection.Port)

                self.__request_status()
            else:
                Domoticz.Debug("OnConnect Error Status: " + str(Status))
                if(Status == 113):  # no route to host error (skip to avoid intempestive connect call)
                    return
                if(self.__connection.Connected()):
                    self.__connection.Disconnect()
                if(not self.__connection.Connecting()):
                    self.__connection.Connect()

    #######################################################################
    #
    # onMessage Domoticz function
    #
    #######################################################################

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called: " + Connection.Address +
                       ":" + Connection.Port + " " + str(Data))

        if (Connection == self.__connection):

            if(self.__state_machine == 0):  # skip nothing was waiting
                return

            if(self.__state_machine == 1):  # after a set command: need to ask the status
                self.__state_machine = 2

            if(self.__state_machine == 2):
                self.__update_status(Data)

    #######################################################################
    #
    # onCommand Domoticz function
    #
    #######################################################################

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) +
                       ": Parameter '" + str(Command) + "' Level: " + str(Level))

        # onCommand called for Unit 2: Parameter 'Set Level' Level: 2.5
        if (Unit == self.__thermostat_device) and (Command == "Set Level"):
            # thermostat setpoint control
            self.__send_update('2', math.floor(2*Level))

        elif (Unit == self.__control_device):
            # thermostat on / off
            if Command == 'Off':
                request_status = False
            elif Command == 'On':
                request_status = True
            else:
                Domoticz.Error("Undefined command for unit " +
                               Unit + ": " + Command)
                return

            self.__send_update('1', request_status)
        elif (Unit == self.__mode_device) and (Command == "Set Level"):
            if Level == 10:
                # manual mode
                request_status = '1'
            elif Level == 20:
                # device built in scheduler
                request_status = '0'
            else:
                Domoticz.Error("Undefined command for unit " +
                               Unit + ": " + Command)
                return

            self.__send_update('4', request_status)
        elif (Unit == self.__eco_device) and (Command == "Set Level"):
            if Level == 10:
                # normal mode
                request_status = False
            elif Level == 20:
                # eco mode
                request_status = True
            else:
                Domoticz.Error("Undefined command for unit " +
                               Unit + ": " + Command)
                return

            self.__send_update('5', request_status)
        elif (Unit == self.__lock_device) and (Command == "Set Level"):
            if Level == 10:
                # unlocked
                request_status = False
            elif Level == 20:
                # locked
                request_status = True
            else:
                Domoticz.Error("Undefined command for unit " +
                               Unit + ": " + Command)
                return

            self.__send_update('6', request_status)
        else:
            Domoticz.Error("Undefined unit (" + str(Unit) +
                           ") or command: '" + str(Command) + "' Level: " + str(Level))
            return

        self.__request_status()

    #######################################################################
    #
    # onDisconnect Domoticz function
    #
    #######################################################################
    def onDisconnect(self, Connection):
        Domoticz.Debug("Disconnected from: " +
                       Connection.Address+":"+Connection.Port)

    #######################################################################
    #
    # onHeartbeat Domoticz function
    #
    #######################################################################
    def onHeartbeat(self):
        self.__runAgain -= 1
        if(self.__runAgain == 0):
            self.__request_status()

    #######################################################################
    #
    # onStop Domoticz function
    #
    #######################################################################
    def onStop(self):
        self.__device = None
        self.__control_device = None
        self.__thermostat_device = None
        if(self.__connection.Connected() or self.__connection.Connecting()):
            self.__connection.Disconnect()
        self.__connection = None
        self.__state_machine = 0


########################################################################################
#
# Domoticz plugin management
#
########################################################################################
global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

################################################################################
# Generic helper functions
################################################################################


def UpdateDevice(Unit, nValue, sValue, TimedOut=0, AlwaysUpdate=False):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if Unit in Devices:
        if Devices[Unit].nValue != nValue or Devices[Unit].sValue != sValue or Devices[Unit].TimedOut != TimedOut or AlwaysUpdate:
            Devices[Unit].Update(
                nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
            Domoticz.Debug(
                "Update " + Devices[Unit].Name + ": " + str(nValue) + " - '" + str(sValue) + "'")
