#!/usr/bin/env python2.7
import printer_health as health
import db as database
import sys
import time
import twilio
from datetime import datetime

class ConfigError(Exception):
    def __init__(self, msg):
        self.value = msg

    def __str__(self):
        return "Config error: %s" % self.value

def check_config():
    try:
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

def send_sms(number, message):
    account = twilio.Account(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    data = {'From': settings.TWILIO_PHONE_NUMBER,
            'To': number,
            'Body': message
    }
    account.request('/%s/Accounts/%s/SMS/Messages' % (settings.TWILIO_API_VERSION, settings.TWILIO_ACCOUNT_SID), \
        'POST', data)

  
def poll():
    db = database.HealthDatabase('polling.db')
    for printer in settings.PRINTERS:
        status = health.get_health(printer)
        pagecount = health.get_pagecount(printer)
        (timestamp, last_status) = db.get_last_status(printer)
        if last_status == None:
            pass
        elif health.is_offline(status) != health.is_offline(last_status):
            message = "Printer '%s' has changed state from '%s' to '%s'" % (printer, 
                health.prettyprint_state(last_status), health.prettyprint_state(status))

            subscribers = db.lookup_subscribers(printer)
            for number in subscribers:
                send_sms(number, message)
            if health.is_offline(status) and not health.is_offline(last_status):
                db.start_outage(printer, health.prettyprint_state(status))
                print "Outage started for %s" % printer
            elif not health.is_offline(status) and health.is_offline(last_status) and db.outage_exists(printer):
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
