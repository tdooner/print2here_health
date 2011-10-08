#!/usr/bin/env python2.7
import sys

import cherrypy
import psycopg2
import psycopg2.extras

from mako.template import Template
from cherrypy.process.plugins import Daemonizer

InterfaceTemplate = Template("""
<!DOCTYPE html>
<head>
<title>Print2Here Metrics</title>
</head>
<body>
<center>
<table border="0">
<tr>
        <th>Printer</th>
        <th>Mean time to failure</th>
        <th>Mean time to repair</th>
        <th>Average pages between outages</th>
        <th>Percent uptime</th>
</tr>
% for row in rows:
<tr>
        <td>${row.name}</td>
        <td>${row.mttf}</td>
        <td>${row.mttr}</td>
        <td>${row.pages}</td>
        <td>${row.uptime}%</td>
</tr>
% endfor
</table>
</center>
</body>
</html>
""")


class Print2HereWeb:
    def index(self):
        db_conn = psycopg2.connect("dbname=print2here user=print2here")
        db_cursor = db_conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        db_cursor.execute("""
SELECT P.name AS name,
(
    SELECT date_trunc('second', AVG(duration)) FROM PeriodsSummary P2
    WHERE P2.name = P.name
    AND P2.status = 'A'
) AS mttf,
(
    SELECT date_trunc('second', AVG(duration)) FROM PeriodsSummary P2
    WHERE P2.name = P.name
    AND P2.status != 'A'
) AS mttr,
(
    SELECT round(AVG(delta_count)) FROM PeriodsSummary P2
    WHERE P2.name = P.name
    AND P2.status = 'A'
) AS pages,
round(((
    (
        SELECT EXTRACT(EPOCH FROM SUM(duration)::interval)
        FROM PeriodsSummary P2
        WHERE P2.status = 'A'
        AND P2.name = P.name
    )
    /
    (
        SELECT EXTRACT(EPOCH FROM (NOW() - MIN(start)))
        FROM PeriodsSummary P2
        WHERE P2.name = P.name
    )
) * 100)::numeric, 2) AS uptime
FROM PeriodsSummary P
GROUP BY name
ORDER BY mttf ASC;
""");
        return InterfaceTemplate.render(rows=db_cursor.fetchall())

    index.exposed = True


if __name__ == "__main__":
    cherrypy.server.socket_host = sys.argv[1]
    cherrypy.server.socket_port = int(sys.argv[2])

    daemon = Daemonizer(cherrypy.engine)
    daemon.subscribe()
    cherrypy.quickstart(Print2HereWeb())
