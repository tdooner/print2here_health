#!/usr/bin/env python2.7
import print2here.snmp
import print2here.db
import print2here.sms
import sys
import time
from datetime import datetime

class ConfigError(Exception):
    def __init__(self, msg):
        self.value = msg

    def __str__(self):
        return "Config error: %s" % self.value

def check_config():
    try:
        if settings.ENABLE_SMS:
            if len(settings.TWILIO_ACCOUNT_SID) != 34:
                raise ConfigError("Twilio account SID is too short to be valid")
            if settings.TWILIO_ACCOUNT_SID[0:2] != 'AC':
                raise ConfigError("Twilio account SID is invalid")
            if len(settings.TWILIO_AUTH_TOKEN) != 32:
                raise ConfigError("Twilio auth token is too short to be valid")
            if settings.TWILIO_PHONE_NUMBER == '':
                raise ConfigError("Twilio phone number not set")
            if settings.TWILIO_API_VERSION == '':
                raise ConfigError("Twilio API version not set")
        if len(settings.PRINTERS) < 1:
            raise ConfigError("No printers set to be polled")
        if not settings.INTERVAL:
            raise ConfigError("Polling interval not set")
    except ConfigError:
        raise
    except Exception, e:
        raise ConfigError(str(e))
  
def poll():
    db = print2here.db.HealthDatabase('polling.db')
    if settings.ENABLE_SMS:
        notifier = print2here.sms.SmsNotifier(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_PHONE_NUMBER, settings.TWILIO_API_VERSION)
    else:
        notifier = None
    for printer in settings.PRINTERS:
        status = print2here.snmp.get_health(printer)
        pagecount = print2here.snmp.get_pagecount(printer)
        (timestamp, last_status) = db.get_last_status(printer)
        if last_status == None:
            pass
        elif print2here.snmp.is_offline(status) != print2here.snmp.is_offline(last_status):
            if settings.ENABLE_SMS:
                message = "Printer '%s' has changed state from '%s' to '%s'" % (printer, 
                    print2here.snmp.prettyprint_state(last_status),
                    print2here.snmp.prettyprint_state(status))

                subscribers = db.lookup_subscribers(printer)
                for number in subscribers:
                    notifier.send_sms(number, message)

            if print2here.snmp.is_offline(status) and not print2here.snmp.is_offline(last_status):
                db.start_outage(printer, print2here.snmp.prettyprint_state(status))
                print "Outage started for %s" % printer
            elif not print2here.snmp.is_offline(status) and print2here.snmp.is_offline(last_status) \
              and db.outage_exists(printer):
                db.end_outage(printer)
                print "Outage ended for %s" % printer
        db.add_status(printer, status, pagecount)


if __name__ == "__main__":
    try:
        import settings
    except ImportError:
        raise ConfigError("settings.py not found")
    check_config()
    while 1:
        poll()
        time.sleep(settings.INTERVAL)
