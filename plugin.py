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
<plugin key="iasmanis_tuya_thermostat_plugin" name="Tuya Thermostat" author="iasmanis" version="3.0.0" externallink=" https://github.com/iasmanis/Domoticz-Tuya-Thermostat-Plugin">
    <params>
        <param field="Address" label="IP address" width="200px" required="true"/>
        <param field="Mode1" label="DevID" width="200px" required="true"/>
        <param field="Mode2" label="Local Key" width="200px" required="true"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="0"   value="0" default="true"/>
                <option label="1"   value="1"/>
                <option label="2"   value="2"/>
                <option label="4"   value="4"/>
                <option label="8"   value="8"/>
                <option label="16"  value="16"/>
                <option label="32"  value="32"/>
                <option label="64"  value="64"/>
                <option label="128" value="128"/>
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

########################################################################################
#
# plug object (represents a socket of the Tuya device)
#
########################################################################################


class DomoticzInputBase:

    #######################################################################
    #
    # constructor
    #
    #######################################################################

    def __init__(self, unit):
        self.__unit = unit
        return

    def put_payload(self, dict_payload):
        raise NotImplementedError


class DomoticzInputThermostat(DomoticzInputBase):

    #######################################################################
    #
    # constructor
    #
    #######################################################################

    def __init__(self, unit):
        self.__setpoint = None  # value for thermostat control
        super(DomoticzInputThermostat, self).__init__(unit)
        return

    #######################################################################
    # update_setpoint function
    #        update the domoticz device
    #
    #######################################################################
    def update_setpoint(self, state):  # state: degrees in x2 whole numbers
        current_temp = round(state/2, 1)
        if(self.__setpoint == current_temp):
            self.__setpoint = None

        UpdateDevice((256 - self.__dps_id), 1, str(current_temp))

        return False

    #######################################################################
    #
    # set_setpoint function
    #         set the setpoint for the next request
    #
    #######################################################################
    def set_setpoint(self, setpoint):
        self.__setpoint = setpoint

    #######################################################################
    #
    # put_payload function
    #        add to dict_payload the command to be sent to the device
    #
    #######################################################################
    def put_payload(self, dict_payload):

        if (self.__setpoint != None):
            dict_payload["2"] = math.ceil(self.__setpoint*2)


########################################################################################

class DomoticzInputSwitch(DomoticzInputBase):

    #######################################################################
    #
    # constructor
    #
    #######################################################################

    def __init__(self, unit):
        self.__command = None        # command ('On'/'Off'/None)
        super(DomoticzInputSwitch, self).__init__(unit)
        return

    #######################################################################
    # update_state function
    #        update the domoticz device
    #        and checks if the last command is equal to the current state
    #
    # parameters:
    #        state: True <=> On ; False <=> Off
    #
    # returns:
    #        True in case of an error (the state does not correspond to the command)
    #        False otherwise
    #######################################################################
    def update_state(self, state):  # state: True <=> On ; False <=> Off

        if(state):
            UpdateDevice(self.__dps_id, 1, "On")

            if(self.__command == 'Off'):
                return True
            else:
                self.__command = None

        elif(self.__alwaysON):  # if not state: need to change the state for always_on devices
            self.__command = 'On'
            return True

        else:
            UpdateDevice(self.__dps_id, 0, "Off")
            if(self.__command == 'On'):
                return True
            else:
                self.__command = None

        return False

    #######################################################################
    #
    # set_command function
    #         set the command for the next request
    #
    #######################################################################
    def set_command(self, cmd):
        if(self.__alwaysON):
            self.__command = 'On'
        else:
            self.__command = cmd

    #######################################################################
    #
    # put_payload function
    #        add to dict_payload the command to be sent to the device
    #
    #######################################################################
    def put_payload(self, dict_payload):

        if (self.__command != None):
            if (self.__command == "On"):
                dict_payload["1"] = True
            else:
                dict_payload["1"] = False


########################################################################################


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
    __VALID_CMD = ('On', 'Off')  # list of valid command

    #######################################################################
    #
    # private functions definition
    #    __extract_status
    #    __is_encoded
    #    __command_to_execute
    #
    #######################################################################

    #######################################################################
    #
    # __extract_status
    #
    # Parameter
    #    Data: a received payload from the tuya smart plug
    #
    # Returns a tuple (bool,dict)
    #    first:  set to True if an error occur and False otherwise
    #    second: dict of the dps (irrelevant if first is True )
    #
    #######################################################################
    def __extract_status(self, Data):

        start = Data.find(b'{"devId')

        if(start == -1):
            return (True, "")

        # in 2 steps to deal with the case where '}}' is present before {"devId'
        result = Data[start:]

        end = result.find(b'}}')

        if(end == -1):
            return (True, "")

        end = end+2
        result = result[:end]
        if not isinstance(result, str):
            result = result.decode()

        try:
            result = json.loads(result)
            return (False, result['dps'])
        except (JSONError, KeyError) as e:
            return (True, "")

    #######################################################################
    #
    # __is_encoded
    #
    # Parameter
    #    Data: a received payload from the tuya smart plug
    #
    # Returns
    #    True if Data is encoded
    #    False otherwise
    #
    # Remark: for debugging purpose
    #
    #######################################################################
    # ~ def __is_encoded(self, Data):

        # ~ tmp = Data[20:-8]  # hard coded offsets
        # ~ if(tmp.startswith(b'3.1')):#PROTOCOL_VERSION_BYTES
            # ~ return True
        # ~ else:
            # ~ return False

    #######################################################################
    #
    # __command_to_execute
    #    send a command (set or status) to the tuya device
    #
    #
    #######################################################################
    def __command_to_execute(self):

        self.__runAgain = self.__HB_BASE_FREQ

        if(self.__connection.Connected()):

            dict_payload = {}

            for key in self.__domoticz_controls:
                self.__domoticz_controls[key].put_payload(dict_payload)

            if(len(dict_payload) != 0):
                self.__state_machine = 1
                payload = self.__device.generate_payload('set', dict_payload)
                self.__connection.Send(payload)

            else:
                self.__state_machine = 2
                payload = self.__device.generate_payload('status')
                self.__connection.Send(payload)

        else:
            if(not self.__connection.Connecting()):
                self.__connection.Connect()

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
        # domotics control ID (On/Off/Auto switch)
        self.__control_device = None
        self.__thermostat_device = None  # mapping between Unit and list of dps id
        self.__domoticz_controls = None  # mapping between dps id and a plug object
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
        self.__control_device = 1
        self.__thermostat_device = 2
        self.__domoticz_controls = {}

        val = 1

        # create domoticz devices
        if(len(Devices) == 0):

            Domoticz.Device(Name="Thermostat Control #" + str(val),
                            Unit=val, Image=15, TypeName="Switch", Used=1).Create()
            Domoticz.Log("Tuya Thermostat Control #" +
                         str(val) + " created.")
            Domoticz.Device(Name="Thermostat #" + str(val),
                            Unit=self.__thermostat_device, Type=242, Subtype=1, Used=1).Create()
            Domoticz.Log("Tuya Thermostat #" + str(val) + " created.")
            self.__domoticz_controls.append(DomoticzInputThermostat())

            Options = {"LevelActions": "|",
                       "LevelNames": "Off|On",
                       "LevelOffHidden": "false",
                       "SelectorStyle": "0"}
            Domoticz.Device(Name="Tuya Thermostat #" + str(val), Unit=self.__control_device,
                            TypeName="Selector Switch", Options=Options).Create()
            Domoticz.Log("Tuya Thermostat Device #" +
                         str(val) + " created.")
            self.__domoticz_controls.append(DomoticzInputSwitch())

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
                self.__command_to_execute()
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
                payload = self.__device.generate_payload('status')
                # TODO active connection check (it should be because we just get a message)
                self.__connection.Send(payload)
                return

            # now self.__state_machine == 2
            self.__state_machine = 0

            (error, state) = self.__extract_status(Data)
            if(error):
                self.__command_to_execute()
                return

            error = False
            for key in self.__domoticz_controls:
                error = error or self.__domoticz_controls[key].update_state(
                    state[str(key)])

            if(error):
                self.__command_to_execute()

    #######################################################################
    #
    # onCommand Domoticz function
    #
    #######################################################################
    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) +
                       ": Parameter '" + str(Command) + "' Level: " + str(Level))

        if (Command == "Set Level"):
            # thermostat setpoint control
            self.__domoticz_controls[self.__thermostat_device].set_setpoint(
                Level)

        elif (Command in self.__VALID_CMD):
            # thermostat on / off
            self.__domoticz_controls[self.__control_device].set_command(
                Command)

        else:
            Domoticz.Error("Undefined command: " + Command)
            return

        self.__command_to_execute()

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
            self.__command_to_execute()

    #######################################################################
    #
    # onStop Domoticz function
    #
    #######################################################################
    def onStop(self):
        self.__device = None
        self.__domoticz_controls = None
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
