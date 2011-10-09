#!/usr/bin/env python2.7
import print2here.snmp
import sys
import time
import psycopg2

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
        if len(settings.PRINTERS) < 1:
            raise ConfigError("No printers set to be polled")
        if not settings.INTERVAL:
            raise ConfigError("Polling interval not set")
    except ConfigError:
        raise
    except Exception, e:
        raise ConfigError(str(e))
  
def poll():
    
    db_conn = psycopg2.connect("dbname=print2here user=print2here")
    db_cursor = db_conn.cursor()

    if settings.ENABLE_SMS:
        notifier = print2here.sms.SmsNotifier(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_PHONE_NUMBER)
    else:
        notifier = None
    for printer in settings.PRINTERS:
        status = print2here.snmp.get_health(printer)
        pagecount = print2here.snmp.get_pagecount(printer)
        db_cursor.execute("SELECT status FROM status WHERE name=%s ORDER BY timestamp DESC LIMIT 1", (printer,))
        try:
            (last_status,) = db_cursor.fetchone()
        except TypeError: 
            last_status = None
        if last_status is not None:    
            if print2here.snmp.is_offline(status) != print2here.snmp.is_offline(last_status):
                if settings.ENABLE_SMS:
                    message = "Printer '%s' has changed state from '%s' to '%s'" % (printer, 
                        print2here.snmp.prettyprint_state(last_status),
                        print2here.snmp.prettyprint_state(status))
                    
                    if print2here.snmp.is_offline(status):
                        db_cursor.execute("SELECT number FROM subscription WHERE name=%s", (printer,)) 
                        for number in db_cursor:
                            try:
                                notifier.send_sms(number, message)
                            except:
                                print "Error while sending SMS to %s" % number
                       
        db_cursor.execute("""
INSERT INTO status (timestamp, name, status, count)
VALUES (CURRENT_TIMESTAMP, %(name)s, %(status)s,
CASE WHEN %(count)s = 0 THEN (SELECT count FROM status WHERE name=%(name)s AND count > 0 ORDER BY timestamp DESC LIMIT 1)
ELSE %(count)s
END)""", {'name': printer, 'status': status, 'count': pagecount})

    db_conn.commit()
    db_cursor.close()
    db_conn.close()

if __name__ == "__main__":
    try:
        import settings
    except ImportError:
        raise ConfigError("settings.py not found")
    check_config()
    if settings.ENABLE_SMS:
        import print2here.sms
    while 1:
        poll()
        time.sleep(settings.INTERVAL)
