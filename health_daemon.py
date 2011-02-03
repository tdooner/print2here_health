#!/usr/bin/env python
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.types import DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import desc

import printer_health as health
import sys
import time
import sqlalchemy
import twilio
from datetime import datetime

db_engine = None
db_session_maker = None
DbBase = declarative_base()

class ConfigError(Exception):
  def __init__(self, msg):
    self.value = msg

  def __str__(self):
    return "Config error: %s" % self.value


class Status(DbBase):
  __tablename__ = "status"

  id = Column(Integer, primary_key = True)
  timestamp = Column(DateTime)
  name = Column(String)
  status = Column(Integer)
  error_flags = Column(Integer)

  def __init__(self, timestamp, name, status):
    self.timestamp = timestamp
    self.name = name
    self.status = status
    self.error_flags = 0

def init_db():
  global db_engine
  global db_session_maker
  db_engine = sqlalchemy.create_engine('sqlite:///polling.db')
  db_metadata = DbBase.metadata
  db_metadata.create_all(db_engine)
  db_session_maker = sessionmaker(bind=db_engine)


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


def get_last_status(name):
  session = db_session_maker()
  status = session.query(Status).filter(Status.name == name).order_by(desc(Status.id)).first()
  if status == None:
    return (None, None)
  return (status.timestamp, status.status)


def add_status(name, status):
  now = datetime.now()  
  session = db_session_maker()
  status_row = Status(now, name, status)
  session.add(status_row)
  session.commit()


def send_sms(number, message):
  account = twilio.Account(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
  data = {'From': settings.TWILIO_PHONE_NUMBER,
          'To': number,
          'Body': message
  }
  account.request('/%s/Accounts/%s/SMS/Messages' % (settings.TWILIO_API_VERSION, settings.TWILIO_ACCOUNT_SID), \
    'POST', data)

  
def poll():
  for printer in settings.PRINTERS:
    status = health.get_health(printer)
    (timestamp, last_status) = get_last_status(printer)
    if last_status == None:
      pass
    elif health.is_offline(status) != health.is_offline(last_status):
      message = "Printer '%s' has changed state from '%s' to '%s'" % (printer, health.prettyprint_state(last_status), health.prettyprint_state(status))
      send_sms(settings.ALERT_NUMBER, message)
      print message
    add_status(printer, status)


if __name__ == "__main__":
  try:
    import settings
  except ImportError:
    raise ConfigError("settings.py not found")
  check_config()
  init_db()
  while 1:
    poll()
    time.sleep(settings.INTERVAL)
