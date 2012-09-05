import unittest
import datetime
import iso8601

import db
from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext import testbed


def date_to_datetime(value):
  """Convert a date to a datetime.

  Args:
    value: A datetime.date object.

  Returns:
    A datetime object with time set to 0:00.
  """
  assert isinstance(value, datetime.date)
  return datetime.datetime(value.year, value.month, value.day)


def time_to_datetime(value):
  """Convert a time to a datetime.

  Args:
    value: A datetime.time object.

  Returns:
    A datetime object with date set to 1970-01-01.
  """
  assert isinstance(value, datetime.time)
  return datetime.datetime(1970, 1, 1,
                           value.hour, value.minute, value.second,
                           value.microsecond)


class Base(db.MoraPolyModel):
    pass

class B(Base):
    # fetches collection of the specified model instances of this
    # collection property and its descendants
    a_set = db.ReverseReferenceProperty('A',
                                        'b_ref',
                                        polymorphic=True)

    # counterintuitively returns siblings of the specified model along
    # with descendants
    c_set = db.ReverseReferenceProperty('C', 'b_ref')

class A(Base):
    b_ref = db.ReferenceProperty(B)

class C(Base):
    b_ref = db.ReferenceProperty(B)


class MoraPolyModelTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()

        # Then activate the testbed, which prepares the service stubs
        # for use.
        self.testbed.activate()

        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def testReverseReference(self):
        b = B()
        b.save()

        a = A(b_ref=b)
        a.save()

        c = C(b_ref=b)
        c.save()

        a_set = b.a_set.fetch(2)
        self.assertEqual(len(a_set), 1)
        self.assertIsInstance(a_set[0], A)

        c_set = b.c_set.fetch(2)
        self.assertEqual(len(c_set), 2)
        self.assertIsInstance(c_set[0], A)
        self.assertIsInstance(c_set[1], C)


class Widget(db.MoraModel):
    # Primitives
    int_ = db.IntegerProperty(default=13)
    float_ = db.FloatProperty(default=1.3)
    bool_ = db.BooleanProperty(default=True)
    str_ = db.StringProperty(default='word')
    text = db.TextProperty(default='word word word')

    # Temporal
    date = db.DateProperty(default=datetime.date(1983, 10, 11))
    time = db.TimeProperty(default=datetime.time(1))
    datetime = db.DateTimeProperty(default=datetime.datetime(1983, 10, 11))

    # Binary data
    byte_str = db.ByteStringProperty(default=b'word')
    blob = db.BlobProperty(default=b'blobword')
    #blob_ref = db.BlobReferenceProperty(default='fake')

    # Special Google Data Protocol & GeoRSS GML Properties
    # These are XML like properties that correspond to GDP and GeoRSS
    geopt = db.GeoPtProperty(default=db.GeoPt(lat=1.3, lon=1.3))
    address = db.PostalAddressProperty(default=db.PostalAddress(
            "1600 Ampitheater Pkwy., Mountain View, CA"))
    phone = db.PhoneNumberProperty(default=db.PhoneNumber(
            "1 (206) 555-1212"))
    email = db.EmailProperty(default=db.Email("larry@example.com"))
    im = db.IMProperty(default=db.IM("http://example.com/", "Larry97"))
    link = db.LinkProperty(default=db.Link("http://www.google.com/"))
    category = db.CategoryProperty(default=db.Category("kittens"))
    rating = db.RatingProperty(default=db.Rating(97))

    # Special User Property
    # TODO: test user property
    # user = db.UserProperty(default=users.User(
    #         email='dude@la.com',
    #         federated_identity='fake'))

    # References
    reference = db.ReferenceProperty(None)
    self_reference = db.SelfReferenceProperty()

    # Lists
    list_ = db.ListProperty(int, default=[13])
    str_list = db.StringListProperty(default=['one'])


class MoraAsJSONTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()

        # Then activate the testbed, which prepares the service stubs
        # for use.
        self.testbed.activate()

        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def testAsJSON(self):
        base = Base()
        base.save()

        widget1 = Widget()
        widget1.save()

        widget = Widget(reference=base,
                        self_reference=widget1)
        widget.save()

        widget = Widget.get(widget.key())
        widgetDict = widget.as_json()

        # primitives
        self.assertIsInstance(widgetDict['int_'], long)
        self.assertIsInstance(widgetDict['float_'], float)
        self.assertIsInstance(widgetDict['bool_'], bool)
        self.assertIsInstance(widgetDict['str_'], basestring)
        self.assertIsInstance(widgetDict['text'], basestring)

        self.assertEqual(widgetDict['int_'], 13)
        self.assertEqual(widgetDict['float_'], 1.3)
        self.assertEqual(widgetDict['bool_'], True)
        self.assertEqual(widgetDict['str_'], 'word')
        self.assertEqual(widgetDict['text'], 'word word word')

        # temporal
        self.assertIsInstance(widgetDict['date'], basestring)
        self.assertIsInstance(widgetDict['time'], basestring)
        self.assertIsInstance(widgetDict['datetime'], basestring)

        self.assertEqual(widgetDict['date'], '1983-10-11T00:00:00+00:00')
        self.assertEqual(widgetDict['time'], '1970-01-01T01:00:00+00:00')
        self.assertEqual(widgetDict['datetime'], '1983-10-11T00:00:00+00:00')

        # binary data
        self.assertIsInstance(widgetDict['byte_str'], basestring)
        self.assertIsInstance(widgetDict['blob'], basestring)
        #self.assertIsInstance(widgetDict['blob_ref'], basestring)

        self.assertEqual(widgetDict['byte_str'], 'd29yZA==')
        self.assertEqual(widgetDict['blob'], 'YmxvYndvcmQ=')
        #self.assertEqual(widgetDict['blob_ref'], 'fake')

        # special properties
        self.assertIsInstance(widgetDict['geopt'], dict)
        self.assertIsInstance(widgetDict['address'], basestring)
        self.assertIsInstance(widgetDict['phone'], basestring)
        self.assertIsInstance(widgetDict['email'], basestring)
        self.assertIsInstance(widgetDict['im'], dict)
        self.assertIsInstance(widgetDict['link'], basestring)
        self.assertIsInstance(widgetDict['category'], basestring)
        self.assertIsInstance(widgetDict['rating'], long)

        self.assertEqual(widgetDict['geopt'], {'lat': 1.3, 'lon': 1.3})
        self.assertEqual(widgetDict['address'],
                         "1600 Ampitheater Pkwy., Mountain View, CA")
        self.assertEqual(widgetDict['phone'], "1 (206) 555-1212")
        self.assertEqual(widgetDict['email'], 'larry@example.com')
        self.assertEqual(widgetDict['im'], {
                'protocol': 'http://example.com/',
                'address': 'Larry97'})
        self.assertEqual(widgetDict['link'], 'http://www.google.com/')
        self.assertEqual(widgetDict['category'], 'kittens')
        self.assertEqual(widgetDict['rating'], 97)

        # special user properties
        # TODO: test user property
        #self.assertIsInstance(widgetDict['user'], dict)

        # references
        self.assertIsInstance(widgetDict['reference'], basestring)
        self.assertIsInstance(widgetDict['self_reference'], basestring)

        self.assertEqual(widgetDict['reference'], str(base.key()))
        self.assertEqual(widgetDict['self_reference'], str(widget1.key()))

        # lists
        self.assertIsInstance(widgetDict['list_'], list)
        self.assertIsInstance(widgetDict['str_list'], list)

        self.assertEqual(widgetDict['list_'], [13])
        self.assertEqual(widgetDict['str_list'], ['one'])


class MoraFromJSONTestCase(unittest.TestCase):
    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()

        # Then activate the testbed, which prepares the service stubs
        # for use.
        self.testbed.activate()

        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def testFromJSON(self):
        widget = Widget()
        widget.save()

        base = Base()
        base.save()

        widget1 = Widget()
        widget1.save()

        widget = Widget.all().fetch(1)[0]
        widget.from_json({
                'int_': 20,
                'float_': 62.3,
                'bool_': False,
                'str_': 'it works!',
                'text': 'long very long text!',

                'date': '1983-04-05T19:36:35.716Z',
                'time': '1983-04-05T19:36:35.716Z',
                'datetime': '1983-04-05T19:36:35.716Z',

                'byte_str': b'aaabbbbaaa',
                'blob': b'blobbbbbbbbbbbbbbbbbbbbbb',
                #'blob_ref': 'nref-blobadjkeu',

                'geopt': {'lat': 13.42, 'lon': 42.13},
                'address': '0001 Cemetery Lane\nNew York, NY',
                'phone': '555-4823',
                'email': 'strongbad@homestarrunner.com',
                'im': {'protocol': 'http://aim.com', 'address': 'dlynch'},
                'link': 'http://apple.com',
                'category': 'lolcatz',
                'rating': 99,

                'reference': str(base.key()),
                'self_reference': str(widget1.key()),
                'list_': [1, 2, 3],
                'str_list': ['a', 'b', 'c']
                })

        self.assertEqual(widget.int_, 20)
        self.assertEqual(widget.float_, 62.3)
        self.assertEqual(widget.bool_, False)
        self.assertEqual(widget.str_, 'it works!')
        self.assertEqual(widget.text, 'long very long text!')

        self.assertEqual(widget.date, datetime.date(1983, 4, 5))
        self.assertEqual(widget.time, datetime.time(19, 36, 35, 716000))
        self.assertEqual(widget.datetime,
                         iso8601.parse_date('1983-04-05T19:36:35.716Z'))

        self.assertEqual(widget.byte_str, 'aaabbbbaaa')
        self.assertEqual(widget.blob, 'blobbbbbbbbbbbbbbbbbbbbbb')
        #self.assertEqual(widget.blob_ref.key(), 'nref-blobadjkeu')

        self.assertEqual(widget.geopt, '13.42,42.13')
        self.assertEqual(widget.address, '0001 Cemetery Lane\nNew York, NY')
        self.assertEqual(widget.phone, '555-4823')
        self.assertEqual(widget.email, 'strongbad@homestarrunner.com')
        self.assertEqual(widget.im, 'http://aim.com dlynch')
        self.assertEqual(widget.link, 'http://apple.com')
        self.assertEqual(widget.category, 'lolcatz')
        self.assertEqual(widget.rating, 99)

        self.assertEqual(widget.reference.key(), base.key())
        self.assertEqual(widget.self_reference.key(), widget1.key())

        self.assertEqual(widget.list_, [1, 2, 3])
        self.assertEqual(widget.str_list, ['a', 'b', 'c'])


        widget.from_json({
                'bool_': True})
        self.assertEqual(widget.bool_, True)

class MoraToJSONTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()

        # Then activate the testbed, which prepares the service stubs
        # for use.
        self.testbed.activate()

        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def testToJSON(self):
        base = Base()
        base.save()

        widget1 = Widget()
        widget1.save()

        widget = Widget(reference=base,
                        self_reference=widget1)
        widget.save()

        widget = Widget.get(widget.key())
        widget_json_str = widget.to_json()

        # TODO: Since the order is not guaranteed (at lease I assume),
        # plus the keys will change one each run we can't simply
        # compare the widget_json_str the string we expect to
        # get. However, we should test the complete widget to
        # to_json()


class MoraNone(db.MoraPolyModel):
    int_ = db.IntegerProperty()
    float_ = db.FloatProperty()
    bool_ = db.BooleanProperty()
    str_ = db.StringProperty()
    txt = db.TextProperty()
    byte_str = db.ByteStringProperty()
    blob = db.BlobProperty()
    date = db.DateProperty()
    time = db.TimeProperty()
    datetime = db.DateTimeProperty()
    geopt = db.GeoPtProperty()
    address = db.PostalAddressProperty()
    phone = db.PhoneNumberProperty()
    email = db.EmailProperty()
    user = db.UserProperty()
    im = db.IMProperty()
    link = db.LinkProperty()
    category = db.CategoryProperty()
    rating = db.RatingProperty()
    reference = db.ReferenceProperty()
    self_reference = db.SelfReferenceProperty()
    blob_reference = db.BlobReferenceProperty()
    list_ = db.ListProperty(int)
    str_list = db.StringListProperty()


class MoraNonePropertiesTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()

        # Then activate the testbed, which prepares the service stubs
        # for use.
        self.testbed.activate()

        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def testNoneProperties(self):
        none = MoraNone()
        none.save()


        ## Integer

        # should be None by default
        self.assertEqual(none.int_, None)
        self.assertEqual(none.as_json()['int_'], None)

        # check inserting an integer
        none.int_ = 1
        none.save()
        self.assertEqual(none.int_, 1)
        self.assertEqual(none.as_json()['int_'], 1)

        # insert None
        none.int_ = None
        none.save()
        self.assertEqual(none.int_, None)
        self.assertEqual(none.as_json()['int_'], None)


        ## Float

        # should be None by default
        self.assertEqual(none.float_, None)
        self.assertEqual(none.as_json()['float_'], None)

        # check inserting a float
        none.float_ = 1.3
        none.save()
        self.assertEqual(none.float_, 1.3)
        self.assertEqual(none.as_json()['float_'], 1.3)

        # insert None
        none.float_ = None
        none.save()
        self.assertEqual(none.float_, None)
        self.assertEqual(none.as_json()['float_'], None)


        ## Boolean

        # should be None by default
        self.assertEqual(none.bool_, None)
        self.assertEqual(none.as_json()['bool_'], None)

        # check inserting a boolean value
        none.bool_ = False
        none.save()
        self.assertEqual(none.bool_, False)
        self.assertEqual(none.as_json()['bool_'], False)

        # insert None
        none.bool_ = None
        none.save()
        self.assertEqual(none.bool_, None)
        self.assertEqual(none.as_json()['bool_'], None)


        ## String

        # should be None by default
        self.assertEqual(none.str_, None)
        self.assertEqual(none.as_json()['str_'], None)

        # check inserting a string
        none.str_ = 'insert a string'
        none.save()
        self.assertEqual(none.str_, 'insert a string')
        self.assertEqual(none.as_json()['str_'], 'insert a string')

        # insert None
        none.str_ = None
        none.save()
        self.assertEqual(none.str_, None)
        self.assertEqual(none.as_json()['str_'], None)


        ## Text

        # should be None by default
        self.assertEqual(none.txt, None)
        self.assertEqual(none.as_json()['txt'], None)

        # check inserting a string
        none.txt = 'insert a string'
        none.save()
        self.assertEqual(none.txt, 'insert a string')
        self.assertEqual(none.as_json()['txt'], 'insert a string')

        # insert None
        none.txt = None
        none.save()
        self.assertEqual(none.txt, None)
        self.assertEqual(none.as_json()['txt'], None)


        ## Byte String

        # should be None by default
        self.assertEqual(none.byte_str, None)
        self.assertEqual(none.as_json()['byte_str'], None)

        # check inserting a string
        none.byte_str = 'insert a string'
        none.save()
        self.assertEqual(none.byte_str, 'insert a string')
        self.assertEqual(none.as_json()['byte_str'], 'aW5zZXJ0IGEgc3RyaW5n')

        # insert None
        none.byte_str = None
        none.save()
        self.assertEqual(none.byte_str, None)
        self.assertEqual(none.as_json()['byte_str'], None)


        ## Blob

        # should be None by default
        self.assertEqual(none.blob, None)
        self.assertEqual(none.as_json()['blob'], None)

        # check inserting a string
        none.blob = 'insert a string'
        none.save()
        self.assertEqual(none.blob, 'insert a string')
        self.assertEqual(none.as_json()['blob'], 'aW5zZXJ0IGEgc3RyaW5n')

        # insert None
        none.blob = None
        none.save()
        self.assertEqual(none.blob, None)
        self.assertEqual(none.as_json()['blob'], None)


        ## Date

        # should be None by default
        self.assertEqual(none.date, None)
        self.assertEqual(none.as_json()['date'], None)

        # check inserting a date
        d = datetime.date(1983, 4, 5)
        none.date = d
        none.save()
        self.assertEqual(none.date, d)
        self.assertEqual(none.as_json()['date'],
                         date_to_datetime(d).isoformat('T') +
                         '+00:00')

        # insert None
        none.date = None
        none.save()
        self.assertEqual(none.date, None)
        self.assertEqual(none.as_json()['date'], None)


        ## Time

        # should be None by default
        self.assertEqual(none.time, None)
        self.assertEqual(none.as_json()['time'], None)

        # check inserting a time
        t = datetime.time(1)
        none.time = t
        none.save()
        self.assertEqual(none.time, t)
        self.assertEqual(none.as_json()['time'],
                         time_to_datetime(t).isoformat('T') +
                         '+00:00')

        # insert None
        none.time = None
        none.save()
        self.assertEqual(none.time, None)
        self.assertEqual(none.as_json()['time'], None)


        ## Datetime

        # should be None by default
        self.assertEqual(none.datetime, None)
        self.assertEqual(none.as_json()['datetime'], None)

        # check inserting datetime
        dt = datetime.datetime(1983, 4, 5)
        none.datetime = dt
        none.save()
        self.assertEqual(none.datetime, dt)
        self.assertEqual(none.as_json()['datetime'],
                         dt.isoformat('T') + '+00:00')

        # insert None
        none.datetime = None
        none.save()
        self.assertEqual(none.datetime, None)
        self.assertEqual(none.as_json()['datetime'], None)


        ## GeoPt

        # should be None by default
        self.assertEqual(none.geopt, None)
        self.assertEqual(none.as_json()['geopt'], None)

        # check inserting a GeoPt
        none.geopt = db.GeoPt('13.1,42.1')
        none.save()
        self.assertEqual(none.geopt, db.GeoPt('13.1,42.1'))
        self.assertEqual(none.as_json()['geopt'],
                         {'lat': 13.1, 'lon': 42.1})

        # insert None
        none.geopt = None
        none.save()
        self.assertEqual(none.geopt, None)
        self.assertEqual(none.as_json()['geopt'], None)


        ## Postal Address

        # should be None by default
        self.assertEqual(none.address, None)
        self.assertEqual(none.as_json()['address'], None)

        # check inserting a PostalAddress
        none.address = db.PostalAddress('0001 Cemetery Lane\nNew York, NY')
        none.save()
        self.assertEqual(none.address,
                         db.PostalAddress('0001 Cemetery Lane\nNew York, NY'))
        self.assertEqual(none.as_json()['address'],
                         '0001 Cemetery Lane\nNew York, NY')

        # insert None
        none.address = None
        none.save()
        self.assertEqual(none.address, None)
        self.assertEqual(none.as_json()['address'], None)


        ## Phone Number

        # should be None by default
        self.assertEqual(none.phone, None)
        self.assertEqual(none.as_json()['phone'], None)

        # check inserting a PhoneNumber
        none.phone = db.PhoneNumber('555-4823')
        none.save()
        self.assertEqual(none.phone, db.PhoneNumber('555-4823'))
        self.assertEqual(none.as_json()['phone'], '555-4823')

        # insert None
        none.phone = None
        none.save()
        self.assertEqual(none.phone, None)
        self.assertEqual(none.as_json()['phone'], None)


        ## Email

        # should be None by default
        self.assertEqual(none.email, None)
        self.assertEqual(none.as_json()['email'], None)

        # check inserting an Email
        none.email = db.Email('strongbad@homestarrunner.com')
        none.save()
        self.assertEqual(none.email, db.Email('strongbad@homestarrunner.com'))
        self.assertEqual(none.as_json()['email'],
                         'strongbad@homestarrunner.com')

        # insert None
        none.email = None
        none.save()
        self.assertEqual(none.email, None)
        self.assertEqual(none.as_json()['email'], None)


        ## IM

        # should be None by default
        self.assertEqual(none.im, None)
        self.assertEqual(none.as_json()['im'], None)

        # check inserting an IM account
        none.im = db.IM('http://aim.com dlynch')
        none.save()
        self.assertEqual(none.im, db.IM('http://aim.com dlynch'))
        self.assertEqual(none.as_json()['im'],
                         {'protocol': 'http://aim.com', 'address': 'dlynch'})

        # insert None
        none.im = None
        none.save()
        self.assertEqual(none.im, None)
        self.assertEqual(none.as_json()['im'], None)


        ## Link

        # should be None by default
        self.assertEqual(none.link, None)
        self.assertEqual(none.as_json()['link'], None)

        # check inserting a Link
        none.link = db.Link('http://apple.com/')
        none.save()
        self.assertEqual(none.link, db.Link('http://apple.com/'))
        self.assertEqual(none.as_json()['link'], 'http://apple.com/')

        # insert None
        none.link = None
        none.save()
        self.assertEqual(none.link, None)
        self.assertEqual(none.as_json()['link'], None)


        ## Category

        # should be None by default
        self.assertEqual(none.category, None)
        self.assertEqual(none.as_json()['category'], None)

        # check inserting a Category
        none.category = db.Category('lolcatz')
        none.save()
        self.assertEqual(none.category, db.Category('lolcatz'))
        self.assertEqual(none.as_json()['category'], 'lolcatz')

        # insert None
        none.category = None
        none.save()
        self.assertEqual(none.category, None)
        self.assertEqual(none.as_json()['category'], None)


        ## Rating

        # should be None by default
        self.assertEqual(none.rating, None)
        self.assertEqual(none.as_json()['rating'], None)

        # check inserting a Rating
        none.rating = db.Rating(99)
        none.save()
        self.assertEqual(none.rating, db.Rating(99))
        self.assertEqual(none.as_json()['rating'], 99)

        # insert None
        none.rating = None
        none.save()
        self.assertEqual(none.rating, None)
        self.assertEqual(none.as_json()['rating'], None)


        ## Reference

        # should be None by default
        self.assertEqual(none.reference, None)
        self.assertEqual(none.as_json()['reference'], None)

        # check inserting a Reference
        base = Base()
        base.save()
        none.reference = base
        none.save()
        self.assertEqual(none.reference.key(), base.key())
        self.assertEqual(none.as_json()['reference'], str(base.key()))

        # insert None
        none.reference = None
        none.save()
        self.assertEqual(none.reference, None)
        self.assertEqual(none.as_json()['reference'], None)


        ## Self Reference

        # should be None by default
        self.assertEqual(none.self_reference, None)
        self.assertEqual(none.as_json()['self_reference'], None)

        # check inserting a SelfReference
        none1 = MoraNone()
        none1.save()

        none.self_reference = none1
        none.save()
        self.assertEqual(none.self_reference.key(), none1.key())
        self.assertEqual(none.as_json()['self_reference'], str(none1.key()))

        # insert None
        none.self_reference = None
        none.save()
        self.assertEqual(none.self_reference, None)
        self.assertEqual(none.as_json()['self_reference'], None)


        ## Blob Reference

        # should be None by default
        # self.assertEqual(none.blob_reference, None)
        # self.assertEqual(none.as_json()['blob_reference'], None)

        # check inserting a BlobReference
        # none.blob_reference = blobstore.BlobKey('fake')
        # none.save()
        # self.assertEqual(none.blob_reference.key(),
        #                  blobstore.BlobKey('fake'))
        # self.assertEqual(none.as_json()['blob_reference'],
        #                  str(blobstore.BlobKey('fake')))

        # insert None
        # none.blob_reference = None
        # none.save()
        # self.assertEqual(none.blob_reference, None)
        # self.assertEqual(none.as_json()['blob_reference'], None)


        ## List

        # should be [] by default, not None
        # TODO: verify this is true with GAE proper
        self.assertEqual(none.list_, [])
        self.assertEqual(none.as_json()['list_'], [])

        # check inserting a list
        none.list_ = [1]
        none.save()
        self.assertEqual(none.list_, [1])
        self.assertEqual(none.as_json()['list_'], [1])

        # can not insert None, must use empty list
        # TODO: verify this is true with GAI proper
        none.list_ = []
        none.save()
        self.assertEqual(none.list_, [])
        self.assertEqual(none.as_json()['list_'], [])


        ## String List

        # should be [] by default, not None
        # TODO: verify this is true with GAE proper
        self.assertEqual(none.str_list, [])
        self.assertEqual(none.as_json()['str_list'], [])

        # check inserting a string list
        none.str_list = ['a']
        none.save()
        self.assertEqual(none.str_list, ['a'])
        self.assertEqual(none.as_json()['str_list'], ['a'])

        # can not insert None, must use empty list
        # TODO: verify this is true with GAE proper
        none.str_list = []
        none.save()
        self.assertEqual(none.str_list, [])
        self.assertEqual(none.as_json()['str_list'], [])
