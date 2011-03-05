from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.types import DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import desc
from datetime import datetime

import sqlalchemy

DbBase = declarative_base()

class Status(DbBase):
    __tablename__ = "status"

    id = Column(Integer, primary_key = True)
    timestamp = Column(DateTime)
    name = Column(String)
    status = Column(Integer)
    count = Column(Integer)
    error_flags = Column(Integer)

    def __init__(self, timestamp, name, status, count):
        self.timestamp = timestamp
        self.name = name
        self.status = status
        self.count = count
        self.error_flags = 0


class Subscription(DbBase):
    __tablename__ = "subscription"

    id = Column(Integer, primary_key = True)
    name = Column(String)
    number = Column(String)

    def __init__(self, name, number):
        self.name = name
        self.number = number


class Outage(DbBase):
    __tablename__ = "outage"

    id = Column(Integer, primary_key = True)
    name = Column(String)
    start = Column(DateTime)
    end = Column(DateTime)
    description = Column(String)
    length = Column(Integer)

    def __init__(self, name, start, end, desc, length):
        self.name = name
        self.start = start
        self.end = end
        self.description = desc
        self.length = length

class HealthDatabase():
    
    db_engine = None
    db_session_maker = None

    # OMG MASSIVE HACK FIX THIS NAOW
    outages = {}

    def __init__(self, dbfile):
        self.db_engine = sqlalchemy.create_engine('sqlite:///%s' % dbfile)
        self.db_metadata = DbBase.metadata
        self.db_metadata.create_all(self.db_engine)
        self.db_session_maker = sessionmaker(bind=self.db_engine)


    def get_last_status(self, name):
        session = self.db_session_maker()
        status = session.query(Status).filter(Status.name == name).order_by(desc(Status.id)).first()
        if status == None:
            return (None, None)
        return (status.timestamp, status.status)


    def add_status(self, name, status, pagecount):
        now = datetime.now()  
        session = self.db_session_maker()
        status_row = Status(now, name, status, pagecount)
        session.add(status_row)
        session.commit()

    # Bleh... should persist this to the db
    def start_outage(self, name, description):
        outage = Outage(name, datetime.now(), None, description, 0)
        self.outages[name] = outage

    def end_outage(self, name):
        outage = self.outages[name]
        outage.end = datetime.now()
        outage.length = (outage.end - outage.start).total_seconds()
        session = self.db_session_maker()
        session.add(outage)
        session.commit()
        del self.outages[name]

    def lookup_subscribers(self, printer):
        subscribers = []
        session = self.db_session_maker()
        query = session.query(Subscription).filter(Subscription.name == printer)
        for subscriber in query.all():
            subscribers.append(subscriber.number)

        return subscribers
