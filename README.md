# Domoticz-Tuya-Thermostat-Plugin

A Domoticz plugin to manage Tuya based thermostat devices


https://www.aliexpress.com/item/32963598720.html?spm=a2g0s.9042311.0.0.27424c4dEOcJDh


## Prerequisites

This plugin is based on the pytuya Python library. For the installation of this library,
follow the Installation guide below.
See [`https://github.com/clach04/python-tuya/`](https://github.com/clach04/python-tuya/) for more information.

For the pytuya Python library, you need pycrypto. pycrypto can be installed with pip:
```
pip3 install pycrypto
```
See [`https://pypi.org/project/pycrypto/`](https://pypi.org/project/pycrypto/) for more information.

## Installation

Assuming that domoticz directory is installed in your home directory.

```bash
cd ~/domoticz/plugins
git clone https://github.com/iasmanis/Domoticz-Tuya-Thermostat-Plugin
cd Domoticz-Tuya-Thermostat-Plugin
git clone https://github.com/clach04/python-tuya.git
ln -s ~/domoticz/plugins/Domoticz-Tuya-Thermostat-Plugin/python-tuya/pytuya pytuya
# restart domoticz:
sudo /etc/init.d/domoticz.sh restart
```
In the web UI, navigate to the Hardware page. In the hardware dropdown there will be an entry called "Tuya SmartThermostat".

## Known issues

1/ python environment

Domoticz may not have the path to the pycrypto library in its python environment.
In this case you will observe something starting like that in the log:
* failed to load 'plugin.py', Python Path used was
* Module Import failed, exception: 'ImportError'

To find where pycrypto is installed, in a shell:
```bash
pip3 show pycrypto
```
The Crypto directory should be present in the directory indicated with Location.

when you have it, just add a symbolic link to it in Domoticz-Tuya-Thermostat-Plugin directory with ```ln -s```.
Example:
```bash
cd ~/domoticz/plugins/Domoticz-Tuya-Thermostat-Plugin
ln -s /home/pi/.local/lib/python3.5/site-packages/Crypto Crypto
```

2/ Tuya app

The tuya app must be close. This limitation is due to the tuya device itself that support only one connection.

3/ Alternative crypto libraries

PyCryptodome or pyaes can be used instead of pycrypto.

## Updating

Like other plugins, in the Domoticz-Tuya-Thermostat-Plugin directory:
```bash
git pull
sudo /etc/init.d/domoticz.sh restart
```

## Parameters

| Parameter | Value |
| :--- | :--- |
| **IP address** | IP of the Smart Thermostat eg. 192.168.1.231 |
| **DevID** | devID of the Smart Thermostat |
| **Local Key** | Local Key of the Smart Thermostat |
| **Debug** | default is 0 |

Helper scripts get_dps.py turnON.py and turnOFF.py can help:
* to determine the dps list
* to check that the needed information are valid (i.e. devID and Local Key) before using the plugin.

## DevID & Local Key Extraction

Recommended method:
[`https://github.com/codetheweb/tuyapi/blob/master/docs/SETUP.md`](https://github.com/codetheweb/tuyapi/blob/master/docs/SETUP.md)

All the information can be found here:
[`https://github.com/clach04/python-tuya/`](https://github.com/clach04/python-tuya/)

## Acknowledgements

* Special thanks for all the hard work of [clach04](https://github.com/clach04), [codetheweb](https://github.com/codetheweb/) and all the other contributers on [python-tuya](https://github.com/clach04/python-tuya) and [tuyapi](https://github.com/codetheweb/tuyapi) who have made communicating to Tuya devices possible with open source code.
* Domoticz team

## References

* Details helping to decode thermostat values [https://www.domoticz.com/forum/viewtopic.php?t=25965](https://www.domoticz.com/forum/viewtopic.php?t=25965)
