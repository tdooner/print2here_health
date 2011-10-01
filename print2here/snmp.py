#!/usr/bin/env python
from pysnmp.entity.rfc3413.oneliner import cmdgen
import sys

UNKNOWN = 0
AVAILABLE = 1
OFFLINE = 2
JAMMED = 3
DOOR_OPEN = 4
NO_TONER = 5
NO_PAPER = 6

class SnmpError(Exception):
    def __init__(self, val):
        self.val = val

    def __str__(self):
        return repr(self.val)

  
class SnmpParseError(Exception):
    def __init__(self, val):
        self.val = val

    def __str__(self):
        return repr(self.val)


def prettyprint_state(state):
    if state == UNKNOWN:
        return "Unknown"
    elif state == AVAILABLE:
        return "Available"
    elif state == OFFLINE:
        return "Offline"
    elif state == JAMMED:
        return "Jammed"
    elif state == DOOR_OPEN:
        return "Door Open"
    elif state == NO_TONER:
        return "No Toner"
    elif state == NO_PAPER:
        return "No Paper"


def is_offline(state):
    if state in (0, 2, 3, 4, 5, 6):
        return True
    elif state in (1,):
        return False


def get_pagecount(hostname):
    errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(
        cmdgen.CommunityData('print2herehealth', 'public'),
        cmdgen.UdpTransportTarget((hostname, 161)),
        (1,3,6,1,2,1,43,10,2,1,4,1,1),
    )
    if errorIndication == 'requestTimedOut':
        return 0 

    if errorStatus:
        raise SnmpError("Unknown error")

    return int(varBinds[0][1])


def get_health(hostname):
    errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(
        cmdgen.CommunityData('print2herehealth', 'public'),
        cmdgen.UdpTransportTarget((hostname, 161)),
        (1,3,6,1,2,1,25,3,2,1,5,1),
        (1,3,6,1,2,1,25,3,5,1,2,1),
    )
    if errorIndication == 'requestTimedOut':
        return OFFLINE 
  
    if errorStatus:
        raise SnmpError("Unknown error")
      
    deviceStatus = varBinds[0][1]
    errorState = ord(varBinds[1][1][0])

    if deviceStatus == 1:
        return UNKNOWN
    if deviceStatus in (2,3,4):
        return AVAILABLE
    if deviceStatus == 5:
        return OFFLINE
    else:
        if errorState & 0x04:
            return JAMMED
        elif errorState & 0x08:
            return DOOR_OPEN
        elif errorState & 0x10:
            return NO_TONER
        elif errorState & 0x40:
            return NO_PAPER
        # All of the above are preferred to a generic "Offline" error
        elif errorState & 0x02:
            return OFFLINE
        # The next two are low paper and low toner, respectively.
        # We can safely assume the printer is available if none
        # of the above errors are flagged.
        elif errorState & 0x80:
            return AVAILABLE
        elif errorState & 0x20:
            return AVAILABLE
        else:
            raise SnmpParseError("Unknown deviceStatus/errorState pair (%s, %s)" % (deviceStatus, errorState))
