# GoProRemote
Controlling a GoPro camera via Wifi RC mode

2019-11-20: Turns out that Smart Remote only uses WiFi and never used BLE - sequence number must not be re-used against Hero 5 and above (re-use was possible in Hero 3). Command set is simplified in Hero 5 but the basics work (PW / CM) with certain commands be accepted with local broadcast address (10.71.79.255). BLE is only available in App Mode as Hero 5 used SSP with random MAC that changes upon connection reset.

2019-03-15: RC mode in Hero 5 and above seems to work differently, and predominantly over BLE. However, BLE pairing in RC mode on Hero 5 seems to suggest that the Smart Remote acts as a peripheral device while the camera acts as a central device. If there is someone that has access to the Smart Remote it would help to produce a dump of the available Bluetooth Service / Characteristics on the remote during pairing. The only command available in Hero 5 over WiFi-RC is "CV" and everything else is ignored (no reply)

## Context
The discovery code was tested against a GoPro Hero 3+ Silver but the believe is that this protocol hasn't changed and thus usable against the current line up of GoPros capable of using Wifi RC mode (Hero 2018 apparently excluded as it might be GoPro App mode only)

## Overview
GoPro that are accessible over Wifi generally has 2 modes: Wifi RC (referred to as RC mode / Smart Remote) and GoPro App (referred to as App mode / GoPro App). There have been extensive research and code around controlling a GoPro in App mode but very few research on RC mode, possibly due to the lack preview capability

## Use case potential
I currently own a Hero3+ Silver and a Hero 5 Black used for recording videos in a track day/HPDE. The current vision is to have a travel router (like the TP-Link TL-WR902AC that I recently acquired) running OpenWRT, simulate a GoPro in App mode, to control multiple GoPro cameras connected via RC mode. Working in tandem with the M Laptimer App from BMW (which has built-in support for GoPro in App mode), the hope is to have iDrve start and stop all GoPro cameras at once along with the telemtry recording

## Setup
To simulate a GoPro smart remote, you will need an Access Point that BSSID matching the GoPro OID prefix (D8:96:85), and an ESSID of the form HERO-RC-###### (the last 6 digit of the BSSID). Once the camera recognized the ESSID, it will no longer needed to be broadcasted. The IP subnet should be 10.71.79.0/24 as Hero 5 and above is hard coded to only respond to 10.71.79.1. There shouldn't be a need to send out a Default Gateway DHCP option either. Once the camera is reachable on the network, it will accept UDP command packets and respond. Smart Remote that has the tag button (which the original WiFi remote doesn't have) now broadcast itself as HERO-RC-#S/N (the suffix being the actual serial number) and the BSSID is no longer restricted to the GoPro OID prefix. Hero 5 will automatically power on when a paired remote turns on and send out a WiFi beacon, as long as it's within the WiFi timeout (even though the WiFi connection gets disassociated when the camera is powered off)

## Protocol
A GoPro camera in RC mode receives command on UDP 8484, and it's technically capable in responding broadcast packets for certain commands depending on the camera version. It will then respond based on the current camera state and the command that was issued. Some rudimentary error checking is performed on the command and included parameters, and if either is invalid, the camera generally responds by indicating as such but further commands might not produce expected payload. In such case, issuing a power off / power on command generally resets the camera back to a working state. There is a lower limit on time between consecutive commands but it's really a cpu cycle limitation.

### Command packet
Command packet is 13 bytes with an optional parameter (mostly 1 byte except for new commands that required 2 bytes, except for the Set date/time command which will require 6 additional bytes). All integer fields are represented in Big-Endian

Offset | Size | Field | Comments
------ | ---- | ----- | --------
0x0 | 8 | Reserved | this must be 0
0x8 | 1 | Subsystem | 0 = command directed at Camera, 1 = command directed at WiFi Bacpac or equivalent
0x9 | 2 | ID | an ID/sequence field that will be echoed back, recommended to be unique and increasing order within power cycle
0xb | 2 | Command | Command code in ASCII
0xd | n | Parameter | Additional parameter for command, between 1 to 6 bytes

### Respond packet
Response packet should be at least 14 bytes

Offset | Size | Field | Comments
------ | ---- | ----- | --------
0x0 | 8 | Reserved | have only seen 0
0x8 | 1 | Subsystem | echoed the Subsystem value of the original command
0x9 | 2 | ID | echoed the ID/sequence of the original command
0xb | 2 | Command | echoed the original command
0xd | 1 | Invalid | sets to 1 if the command failed to execute or recognize
0xe | n | Return | Data returned by the command, generally matching the original parameter.

## Implementation
Because the vision is to run inside an OpenWRT router, micropython is used. There are some differences compared to the full blown python and the OpenWRT implementation has very little documentation. A lot of trial and error was involved to come out with the functions to achieve certain output

NodeJS will be used for implementing on Raspberry Pi.

## Rule of thumb
* Available commands tend to match the Hero2/Hero3 App mode commands (Hero4 and above has completely revamped the App mode API)
* Even if the command is accepted, the desired function might not be available (e.g. Preview)
* Lower cased commands are queries, while upper cased commands are sets
* Parameter checking is not as tight as it should so sometimes a camera will accept certain parameter value and not react well to it (e.g. Photo Resolution of 5mp Medium perspective can be specified in 2 ways)
* Hero 5 checks that the ID/sequence number hasn't be used and will not execute on commands that were below its last received sequence number

## Credits
[KonradIT](https://github.com/KonradIT/) - multiple projects, but mainly from https://github.com/KonradIT/goprowifihack

[theContentMint/GoProRemote](https://github.com/theContentMint/GoProRemote)

[joshvillbrandt/goprohero](https://github.com/joshvillbrandt/goprohero) - specifically, [docs/Wifi Research](https://github.com/joshvillbrandt/goprohero/blob/master/docs/Wifi%20Research.md)

Other sources to be sited
