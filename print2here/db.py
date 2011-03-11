from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.types import DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql.expression import *
from sqlalchemy import func
from sqlalchemy.orm.exc import *
from datetime import datetime

import sqlalchemy
import snmp

DbBase = declarative_base()

class DatabaseEmptyException(Exception):
    pass


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


class PageCounter(DbBase):
    __tablename__ = "page_count"

    id = Column(Integer, primary_key = True)
    name = Column(String)
    last_status_id = Column(Integer, ForeignKey('status.id'))
    count = Column(Integer)

    def __init__(self, name, last_status, count):
        self.name = name
        self.last_status_id = last_status
        self.count = count


class HealthDatabase():
    
    db_engine = None
    db_session_maker = None

    def __init__(self, dbfile, check_cache = True):
        self.db_engine = sqlalchemy.create_engine('sqlite:///%s' % dbfile)
        self.db_metadata = DbBase.metadata
        self.db_metadata.create_all(self.db_engine)
        self.db_session_maker = sessionmaker(bind=self.db_engine)
        if check_cache:
            self.do_cache_check()

    def do_cache_check(self):
        try:
            last_poll_time = self.get_db_end()
        except DatabaseEmptyException:
            return

        # Flush outages if db is more than 10 minutes old
        if (datetime.now() - last_poll_time).total_seconds() > 600:
            session = self.db_session_maker()
            session.query(Outage).filter(Outage.end == None).delete()

    def get_last_status(self, name):
        session = self.db_session_maker()
        status = session.query(Status).filter(Status.name == name).order_by(desc(Status.id)).first()
        if status == None:
            return (None, None)
        return (status.timestamp, status.status)

    def get_db_start(self):
        session = self.db_session_maker()
        return session.query(Status).first().timestamp

    def get_db_end(self):
        session = self.db_session_maker()
        try:
            return session.query(Status).order_by(desc(Status.timestamp)).first().timestamp
        except AttributeError:
            raise DatabaseEmptyException

    def get_downtime(self, name):
        session = self.db_session_maker()
        cursor = session.query(func.sum(Outage.length)).filter(Outage.name == name)
        if not cursor.scalar():
            return 0
        return cursor.scalar()

    def get_average_downtime(self, name):
        session = self.db_session_maker()
        cursor = session.query(func.avg(Outage.length)).filter(Outage.name == name)
        if not cursor.scalar():
            return 0
        return cursor.scalar()

    def add_status(self, name, status, pagecount):
        now = datetime.now()  
        session = self.db_session_maker()
        status_row = Status(now, name, status, pagecount)
        session.add(status_row)
        session.commit()

    def start_outage(self, name, description):
        session = self.db_session_maker()
        outage = Outage(name, datetime.now(), None, description, 0)
        session.add(outage)
        session.commit()

    def end_outage(self, name):
        session = self.db_session_maker()

        # Technically this can raise an exception, but the db is probably fucked if it does
        # so halting is the safest option (indicates that a second process is hitting the 
        # db at the same time, or our cache clear isn't working properly)
        outage = session.query(Outage).filter(Outage.name == name).filter(Outage.end == None).one()
        outage.end = datetime.now()
        outage.length = (outage.end - outage.start).total_seconds()
        session.add(outage)
        session.commit()

    def outage_exists(self, name):
        session = self.db_session_maker()
        try:
            session.query(Outage).filter(Outage.name == name).filter(Outage.end == None).one()
        except NoResultFound:
            return False
        return True

    def lookup_subscribers(self, printer):
        subscribers = []
        session = self.db_session_maker()
        query = session.query(Subscription).filter(Subscription.name == printer)
        for subscriber in query.all():
            subscribers.append(subscriber.number)

        return subscribers

    def update_page_counts(self, printer):
        session = self.db_session_maker()
        try:
            counter = session.query(PageCounter).filter(PageCounter.name == printer).one()
        except NoResultFound:
            first_update = session.query(Status).filter(Status.name == printer).first()
            counter = PageCounter(printer, first_update.id, 0)
        newer_updates = session.query(Status).filter(Status.name == printer)\
            .filter(Status.id > counter.last_status_id)

        # This is a massive hack because SQLAlchemy doesn't use an iterator interface on its
        # Query objects. This will most likely need to be changed so that it implements its own
        # iterator in the future, as loading a subset of the entire Status table is probably
        # going to be very slow at some point in the near future (the .all() method executes
        # the SELECT and returns the data as a Python list (yeah, painful, I know))
        # The other option is to add a "delta" field to the Status table, but that would require
        # a SELECT of 2+ prior rows in cases where the printer is offline and reporting a 0 page count
        # so that we can properly determine the delta value using the last known good update
        prior_update = None
        for update in newer_updates.all():
            if prior_update == None:
                prior_update = update
                continue
            if update.status != snmp.AVAILABLE:
                continue
            delta = update.count - prior_update.count
            if delta > 0:
                counter.count += delta
            elif delta < -50:
                # Most likely case is that the printer was rebooted and the counter objects
                # in SNMP were reset, so that the current count reflects the number of pages
                # since the initial value of 0. We can safely add the count by itself.
                # Sometimes the printers seem to randomly decrement their page counts by a small
                # number, so we guard against this by making sure there's a large negative delta.
                # It's extremely ghetto, but should suffice without losing accuracy.
                counter.count += update.count
            prior_update = update
        if prior_update:
            counter.last_status_id = prior_update.id
        session.add(counter)
        session.commit()
