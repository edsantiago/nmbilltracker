#!/usr/bin/env python3

#
# NOTE: The tests use sqlite as the database,
# which may not be what the production app uses.
#

import sys, os
sys.path.insert(1, os.path.join(sys.path[0], '..'))

import unittest
from unittest import mock

import re

from billtracker import billtracker, db
from billtracker.models import User, Bill
from config import Config, basedir


TEST_DB = 'test/cache/test.db'

# This method will be used by the mock to replace requests.get
def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, text, status_code):
            self.text = text
            self.status_code = status_code

    # print("******** mocked response, args =", args)
    realurl = args[0]
    m = re.match('https?://www.nmlegis.gov/Legislation/Legislation\?chamber=(.)&legtype=(.)&legno=(\d+)&year=(\d\d)', realurl)
    if m:
        chamber, legtype, billno, year = m.groups()
        filename = 'test/cache/20%s-%s%s%s.html' % (year, chamber,
                                                    legtype, billno)
        if os.path.exists(filename):
            with open(filename) as fp:
                return MockResponse(fp.read(), 200)
        print("Cache filename", filename, "doesn't exist")
    elif realurl == "https://www.nmlegis.gov/Legislation/Legislation_List":
        filename = "test/cache/Legislation_List.html"
        with open(filename) as fp:
            return MockResponse(fp.read(), 200)
    else:
        print("URL '%s' didn't match a pattern" % realurl)

    return MockResponse(None, 404)


class TestBillTracker(unittest.TestCase):
    # setUp() will be called for every test_*() function in the class.
    def setUp(self):
        self.key = 'TESTING_NOT_SO_SECRET_KEY'

        billtracker.config['TESTING'] = True
        billtracker.config['SECRET_KEY'] = self.key

        self.dbname = os.path.join(basedir, TEST_DB)
        billtracker.config['SQLALCHEMY_DATABASE_URI'] = \
            'sqlite:///' + self.dbname

        self.app = billtracker.test_client()

        db.drop_all()
        db.create_all()


    def tearDown(self):
        db.session.remove()
        db.drop_all()
        os.unlink(self.dbname)


    def test_password_hashing(self):
        u = User(username='testuser')
        u.set_password('testpassword')
        self.assertFalse(u.check_password('notthepassword'))
        self.assertTrue(u.check_password('testpassword'))


    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_bills_and_users(self, mock_get):
        '''Test adding new users and bills to the database.'''
        # Users and bills depend on each other, so they pretty much
        # need to be combined in the same test.

        # Check that the home page loads.
        # This has nothing to do with bills, but calling setUp/tearDown
        # just for this would be a waste of cycles.
        # This will redirect to the login page, login().
        response = self.app.get('/index', follow_redirects=True)
        self.assertTrue(response.status_code == 200 or
                        response.status_code == 302)

        # Add a new bill, using the already cached page
        response = self.app.post("/api/refresh_one_bill",
                                 data={ 'BILLNO': 'HB73', 'KEY': self.key,
                                        'YEARCODE': '19'} )
        self.assertTrue(response.status_code == 200 or
                        response.status_code == 302)
        self.assertEqual(response.get_data(as_text=True), 'OK Updated HB73')

        # There should be exactly one bill in the database now
        allbills = Bill.query.all()
        self.assertEqual(len(allbills), 1)

        # Test that bills_by_update_date now shows the bill
        response = self.app.get("/api/bills_by_update_date",
                                data={ 'yearcode': '19' })
        self.assertEqual(response.get_data(as_text=True), 'HB73')

        # Test whether the bill just added is in the database
        bill = Bill.query.filter_by(billno="HB73").first()
        self.assertEqual(bill.billno, "HB73")
        self.assertEqual(bill.title, 'EXEMPT NM FROM DAYLIGHT SAVINGS TIME')

        # Add a bill that has mostly null fields
        bill = Bill()
        billdata = {
            'billno': 'HB100',
            'chamber': 'H',
            'billtype': 'B',
            'number': '100',
            'year': '19',
            'title': 'BILL WITH NULL STUFF',
            'sponsor': None,
            'sponsorlink': None,
            'contentslink': None,
            'amendlink': None,
            'last_action_date': None,
            'statusHTML': None,
            'statustext': None,
            'FIRlink': None,
            'LESClink': None,
            'update_date': None,
            'mod_date': None
        }
        bill.set_from_parsed_page(billdata)
        db.session.add(bill)
        db.session.commit()

        # This is needed to test WTForms to test any POSTs:
        billtracker.config['WTF_CSRF_ENABLED'] = False

        # Create a user.
        # Don't set email address, or it will try to send a confirmation mail.
        USERNAME = "testuser"
        PASSWORD = "testpassword"
        response = self.app.post("/newaccount",
                                 data={ 'username': USERNAME,
                                        'password': PASSWORD,
                                        'password2': PASSWORD,
                                        'submit': 'Register' })
        self.assertTrue(response.status_code == 200 or
                        response.status_code == 302)
        allusers = User.query.all()
        self.assertEqual(len(allusers), 1)
        user = User.query.filter_by(username='testuser').first()
        self.assertEqual(user.username, 'testuser')

        # Try addbills without being logged in:
        response = self.app.post('/addbills',
                                 data={ 'billno':   'HB73',
                                        'yearcode': '19',
                                        'submit':   'Track a Bill'})
        self.assertTrue(response.status_code == 200 or
                        response.status_code == 302)
        self.assertEqual(response.headers['location'],
                         'http://localhost/login?next=%2Faddbills')

        response = self.app.post('/login', data=dict(
            username=USERNAME,
            password=PASSWORD
        ), follow_redirects=True)
        self.assertTrue(response.status_code == 200 or
                        response.status_code == 302)
        text_response = response.get_data(as_text=True)
        self.assertTrue("Warning: Your email hasn't been confirmed yet"
                        in text_response)
        self.assertTrue("Bills testuser is tracking:"
                        in text_response)
        self.assertTrue("This is your first check"
                        in text_response)



        # view the index with yearcode 19, to set the yearcode in the session.
        response = self.app.get("/?yearcode=19")
        self.assertTrue(response.status_code == 200 or
                        response.status_code == 302)

        # Now try addbills again as a logged-in user:
        response = self.app.post('/addbills',
                                 data={ 'billno': 'HB73',
                                        'yearcode': '19',
                                        'submit': 'Track a Bill'})
        self.assertTrue(response.status_code == 200 or
                        response.status_code == 302)
        response = self.app.post('/addbills',
                                 data={ 'billno': 'HB100',
                                        'yearcode': '19',
                                        'submit': 'Track a Bill'})
        self.assertTrue(response.status_code == 200 or
                        response.status_code == 302)

        # Need to re-query the user to get the updated bill list:
        user = User.query.filter_by(username='testuser').first()

        self.assertEqual(len(user.bills), 2)
        self.assertEqual(user.bills[0].billno, 'HB73')

        # Now test the index page again
        response = self.app.get('/', follow_redirects=True)
        self.assertTrue(response.status_code == 200 or
                        response.status_code == 302)
        pageHTML = response.get_data(as_text=True)
        self.assertTrue('HB73' in pageHTML)
        self.assertTrue('HB100' in pageHTML)


if __name__ == '__main__':
    unittest.main(verbosity=2)
