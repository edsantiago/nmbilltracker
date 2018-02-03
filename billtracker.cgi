#!/usr/bin/env python3

import cgi
# CGI tracebacks:
import cgitb
cgitb.enable()

import billdb
import nmlegisbill

# While testing, use local files:
nmlegisbill.url_mapper = \
    nmlegisbill.LocalhostURLmapper('http://localhost/billtracker',
                                   'https://www.nmlegis.gov')

print('''Content-type: text/html

<html>
<head>
<title>New Mexico Bill Tracker</title>
</head>

<body>
<h1>New Mexico Bill Tracker</h1>
''')

def show_bill_list(bills):
    print("<dl>")
    for bill in bills:
        print("<dt>", bill)
        billdic = nmlegisbill.parse_bill_page(bill, 2018)
        if not billdic:
            print("<dt>Error: couldn't find bill", bill)
            continue
        for key in billdic:
            val = billdic[key]
            if key.endswith("url") or key.endswith("link"):
                print("<dd>%s: <a href='%s'>%s</a>" % (key, val, val))
            else:
                print("<dd>%s: %s" % (key, val))
    print("</dl>")

form = cgi.FieldStorage()

if "bills" in form:
    bills = form["bills"].value.split(',')
    print("<p>\nBills:", form["bills"].value)
    show_bill_list(bills)

if "user" in form:
    print("<p>\nBills <b>%s</b> is tracking:" % form["user"].value)

    billdb.init()

    bills = billdb.get_user_bills(form["user"].value)
    show_bill_list(bills)

if not form.keys():
    print("Username?")

print("</body></html>")


