# GoProRemote
Controlling a GoPro camera via Wifi RC mode

## Context
The discovery code was tested against a GoPro Hero 3+ Silver but the believe is that this protocol hasn't changed and thus usable against the current line up of GoPros capable of using Wifi RC mode (Hero 2018 apparently excluded as it might be GoPro App mode only)

## Overview
GoPro that are accessible over Wifi generally has 2 modes: Wifi RC (referred to as RC mode) and GoPro App (referred to as App mode). There have been extensive research and code around controlling a GoPro in App mode but very few research on RC mode, possibly due to the lack preview capability

## Use case potential
I currently own a single Hero3+ Silver used for recording videos in a track day/HPDE. The current vision is to have a travel router (like the TP-Link TL-WR902AC that I recently acquired) running OpenWRT, simulate a GoPro in App mode, to control multiple GoPro cameras connected via RC mode. Working in tandem with the M Laptimer App from BMW (which has built-in support for GoPro in App mode), the hope is to have iDrve start and stop all GoPro cameras at once along with the telemtry recording

## Setup
To simulate a GoPro smart remote, you will need an Access Point that BSSID matching the GoPro OID prefix (D8:96:85), and an ESSID of the form HERO-RC-###### (the last 6 digit of the BSSID). Once the camera recognized the ESSID, it will no longer needed to be broadcasted. The IP subnet didn't matter although I would avoid assigning 10.5.5.0/24 or 10.9.9.0/24 (neither is exposed from the GoPro under RC mode). There shouldn't be a need to send out a Default Gateway DHCP option either. Once the camera is reachable on the network, it will accept UDP command packets and respond

## Protocol
A GoPro camera in RC mode receives command on UDP 8484, and it's technically capable in responding broadcast packets. It will then respond based on the current camera state and the command that was issued. Some rudimentary error checking is performed on the command and included parameters, and if either is invalid, the camera generally responds by indicating as such but further commands might not produce expected payload. In such case, issuing a power off / power on command generally resets the camera back to a working state. There is a lower limit on time between consecutive commands but it's really a cpu cycle limitation.

### Command packet
Command packet is 13 bytes with an optional 1 byte parameter (except for the Set date/time command which will require 6 additional bytes). All integer fields are represented in Big-Endian

Offset | Size | Field | Comments
------ | ---- | ----- | --------
0x0 | 8 | Reserved | this must be 0
0x8 | 1 | Flag | some commands can support 2 formats, must be 0 or 1
0x9 | 2 | ID | an ID/sequence field that will be echoed back
0xb | 2 | Command | Command code in ASCII
0xd | n | Parameter | Additional parameter for command, usually 1 byte

### Respond packet
Response packet should be at least 14 bytes unless the command was deemed invalid.

Offset | Size | Field | Comments
------ | ---- | ----- | --------
0x0 | 8 | Reserved | have only seen 0
0x8 | 1 | Flag | echoed the flag value of the original command
0x9 | 2 | ID | echoed the ID/sequence of the original command
0xb | 2 | Command | echoed the original command
0xd | 1 | Invalid | sets to 1 if the command failed to execute - payload ends here in this case
0xe | n | Return | Data returned by the command, generally matching the original parameter.

## Implementation
Because the vision is to run inside an OpenWRT router, micropython is used. There are some differences compared to the full blown python and the OpenWRT implementation has very little documentation. A lot of trial and error was involved to come out with the functions to achieve certain output

## Rule of thumb
* Available commands tend to match the Hero2/Hero3 App mode commands (Hero4 and above has completely revamped the App mode API)
* Even if the command is accepted, the desired function might not be available (e.g. Preview)
* Lower cased commands are queries, while upper cased commands are sets
* Parameter checking is not as tight as it should so sometimes a camera will accept certain parameter value and not react well to it (e.g. Photo Resolution of 5mp Medium perspective can be specified in 2 ways)

## Credits
[KonradIT](https://github.com/KonradIT/) - multiple projects, but mainly from https://github.com/KonradIT/goprowifihack

[theContentMint/GoProRemote](https://github.com/theContentMint/GoProRemote)

[joshvillbrandt/goprohero](https://github.com/joshvillbrandt/goprohero) - specifically, [docs/Wifi Research](https://github.com/joshvillbrandt/goprohero/blob/master/docs/Wifi%20Research.md)

Other sources to be sited
