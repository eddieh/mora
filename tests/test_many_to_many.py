import unittest

import db
from google.appengine.ext import testbed

class ManyToManyTestCase(unittest.TestCase):

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

    def test_configuration_error(self):
        with self.assertRaises(db.ConfigurationError):
            class A(db.MoraModel):
                reverse_ref = db.ReverseReferenceProperty(
                    'User',
                    'course',
                    through='CourseMembership')

        with self.assertRaises(db.ConfigurationError):
            class A(db.MoraModel):
                reverse_ref = db.ReverseReferenceProperty(
                    'User',
                    'course',
                    through_prop='user')

    def test_reverse_reference(self):
        class User(db.MoraModel):
            name = db.StringProperty()
            courses = db.ReverseReferenceProperty(
                'Course',
                'user',
                through='CourseMembership',
                through_prop='course')

        class Course(db.MoraModel):
            name = db.StringProperty()
            users = db.ReverseReferenceProperty(
                'User',
                'course',
                through='CourseMembership',
                through_prop='user')

        class CourseMembership(db.MoraModel):
            user = db.ReferenceProperty('User')
            course = db.ReferenceProperty('Course')

        user1 = User(name='Eddie')
        user1.save()
        user2 = User(name='Sharon')
        user2.save()
        user3 = User(name='Bob')
        user3.save()

        course1 = Course(name='CS 126')
        course1.save()
        course2 = Course(name='CS 136')
        course2.save()
        course3 = Course(name='CS 249')
        course3.save()

        CourseMembership(user=user1, course=course1).save()
        CourseMembership(user=user1, course=course2).save()

        CourseMembership(user=user2, course=course1).save()
        CourseMembership(user=user2, course=course2).save()

        CourseMembership(user=user3, course=course2).save()
        CourseMembership(user=user3, course=course3).save()

        user1_courses = user1.courses.fetch(10)
        self.assertEqual(len(user1_courses), 2)
        self.assertEqual(user1_courses[0].name, 'CS 126')
        self.assertEqual(user1_courses[1].name, 'CS 136')

        user2_courses = user2.courses.fetch(10)
        self.assertEqual(len(user2_courses), 2)
        self.assertEqual(user2_courses[0].name, 'CS 126')
        self.assertEqual(user2_courses[1].name, 'CS 136')

        user3_courses = user3.courses.fetch(10)
        self.assertEqual(len(user3_courses), 2)
        self.assertEqual(user3_courses[0].name, 'CS 136')
        self.assertEqual(user3_courses[1].name, 'CS 249')

        course2_users = course2.users.fetch(10)
        self.assertEqual(len(course2_users), 3)
        self.assertEqual(course2_users[0].name, 'Eddie')
        self.assertEqual(course2_users[1].name, 'Sharon')
        self.assertEqual(course2_users[2].name, 'Bob')

    def test_with_filter_function(self):
        class User(db.MoraModel):
            name = db.StringProperty()
            courses = db.ReverseReferenceProperty(
                'Course',
                'user',
                through='CourseMembership',
                through_prop='course',
                filter_function=lambda query:
                    query.filter('active =', True))

        class Course(db.MoraModel):
            name = db.StringProperty()
            users = db.ReverseReferenceProperty(
                'User',
                'course',
                through='CourseMembership',
                through_prop='user')

        class CourseMembership(db.MoraModel):
            user = db.ReferenceProperty('User')
            course = db.ReferenceProperty('Course')
            active = db.BooleanProperty()

        user1 = User(name='Eddie')
        user1.save()

        course1 = Course(name='CS 126')
        course1.save()
        course2 = Course(name='CS 136')
        course2.save()

        CourseMembership(user=user1, course=course1, active=False).save()
        CourseMembership(user=user1, course=course2, active=True).save()

        user1_courses = user1.courses.fetch(10)
        self.assertEqual(len(user1_courses), 1)
        self.assertEqual(user1_courses[0].name, 'CS 136')
