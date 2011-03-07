#!/usr/bin/env python2.7

from __future__ import division

import settings
import db as database

pages = {}

db = database.HealthDatabase('polling.db')

polling_start = db.get_db_start() 
polling_end = db.get_db_end()
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
  downtime = db.get_downtime(printer) 
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
