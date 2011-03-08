#!/usr/bin/env python2.7

from __future__ import division

import settings
import db as database

pages = {}

def seconds_to_string(seconds):
    string = ""
    # Since we're using __future__, / is remapped to //
    days = seconds // (60 * 60 * 24)
    seconds %= (60 * 60 * 24)
    hours = seconds // (60 * 60)
    seconds %= (60 * 60)
    minutes = seconds // 60
    seconds %= 60
    if days > 1:
        string += "%i days, " % days
    elif days == 1:
        string += "1 day, "
    if hours > 1:
        string += "%i hours, " % hours
    elif hours == 1:
        string += "1 hour, "
    if minutes > 1:
        string += "%i minutes, " % minutes
    elif minutes == 1:
        string += "1 minute, "
    if seconds > 1:
        string += "%i seconds  " % seconds
    elif seconds == 1:
        string += "1 second  "
    return string[:-2]


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
    <td>Average Outage Length</td>
  </tr>""")

for printer in settings.PRINTERS:
    downtime = db.get_downtime(printer) 
    avg_downtime = db.get_average_downtime(printer)
    percent = round(((1 - (downtime / polling_length)) * 100), 2)
    output.write("""
  <tr>
    <td>%s</td>
    <td>%s%%</td>
    <td>%s</td>
  </tr>""" % (printer, percent, seconds_to_string(avg_downtime)))

output.write("""
</table>
</center>
Statistics gathered from %s to %s
</body>
</html>""" % (polling_start.strftime('%Y-%m-%d %H:%M:%S'), polling_end.strftime('%Y-%m-%d %H:%M:%S')))
