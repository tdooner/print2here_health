#!/usr/bin/env python2.7

from __future__ import division

import settings
import health_daemon as daemon
from sqlalchemy.sql.expression import *
from sqlalchemy import func

pages = {}

daemon.init_db()
session = daemon.db_session_maker()

polling_start = session.query(daemon.Status).first().timestamp
polling_end = session.query(daemon.Status).order_by(desc(daemon.Status.timestamp)).first().timestamp
polling_length = round((polling_end - polling_start).total_seconds())

output = open(settings.REPORT_PAGE_PATH, 'w')

output.write("""<!DOCTYPE html>
<html>
<head>
  <title>Print2Here Reliability Statistics</title>
</head>
<body>
<center>
<table border="1">
  <tr>
    <td>Printer</td>
    <td>Percent Uptime</td>
  </tr>""")

for printer in settings.PRINTERS:
  cursor = session.query(func.sum(daemon.Outage.length)).filter(daemon.Outage.name == printer)
  downtime = cursor.scalar()
  if not downtime:
    downtime = 0
  percent = round(((1 - (downtime / polling_length)) * 100), 2)
  output.write("""
  <tr>
    <td>%s</td>
    <td>%s%%</td>
  </tr>""" % (printer, percent))

output.write("""
</table>
</center>
Statistics gathered from %s to %s
</body>
</html>""" % (polling_start.strftime('%Y-%m-%d %H:%M:%S'), polling_end.strftime('%Y-%m-%d %H:%M:%S')))
