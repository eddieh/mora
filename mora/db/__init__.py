#     (c) 2012 James Dean Palmer
#     (c) 2007 Google Inc.
#     Mora may be freely distributed under the Apache 2.0
#     licence.  You may obtain a copy of this license at
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     For all details and coumentation:
#     http://jdpalmer.github.com/mora

# *Mora* provides restful services and richer [JSON][json] support for
# [Google App Engine][gae] (GAE). Mora intends to be lightweight and
# unobtrusive.
# [gae]: http://code.google.com/appengine/ "Google App Engine"
# [json]: http://www.json.org/ "JavaScript Object Notation"

### Motivation

# One of the most important things that Mora adds to GAE models and
# properties is a mechanism for generating JSON.  I have adopted
# [Rails][rails]-style `to_json` and `as_json` methods and have
# specifically avoided placing this logic in a [JSONEncoder][jsone]
# subclass.  There's a few reasons for this - the first is that such a
# subclass would have to know about all of App Engine's types and
# models.  If you add new types and classes you have to modify or
# further subclass the encoder. And if third-party libraries use their
# own JSONEncoder subclass, you have the unenviable task of patching
# the variations to work together. There's also a real danger in
# putting business logic in your encoder because the easy to place to
# filter and manipulate JSON properties is where they are being
# generated.  Last time I checked there was no
# Model-View-Controller-JSONEncoder paradigm.  The JSONEncoder is the
# wrong place to make view decisions or business logic decisions.
#
# Rails has split the JSON rendering process into [two parts][julian].
# A method called `as_json` is used to build a representation made of
# core JSON-types.  `as_json` is the smart half of the equation and
# belongs to the Model and can make business logic decisions.
# `to_json` then calls the json encoder and that's pretty much all it
# does.
#
# Mora adopts this philoshopy and adds `as_json` to GAE's models *and*
# types.  If you add new models and types and also add the `as_json`
# method it will all just work (TM).
# [julian]:
# http://jonathanjulian.com/2010/04/rails-to_json-or-as_json/ "Rails
# to_json or as_json?"
# [rails]: http://rubyonrails.org/ "Ruby on Rails"
# [jsone]: http://docs.python.org/library/json.html "JSON in Python"

### Dependencies

# We import some standard modules and also Google App Engine's `db`
# and `polymodel` modules.  We have to dig at GAE's guts a bit to
# shoehorn in better per type JSON support but most of this can be
# accomplished with simple subclassing.
import logging
import base64
import datetime
import dateutil.parser

from xml.sax import saxutils
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from google.appengine.api import datastore
from google.appengine.api import users
from google.appengine.ext import blobstore

# GAE supports a couple of versions of Python and the GAE environment.
# We will try to use the latest modules and then use `ImportError`
# exceptions to select older variations.
try:
    import json
except ImportError:
    from django.utils import simplejson as json

try:
    import webapp2 as webapp
except ImportError:
    from google.appengine.ext import webapp

### Keys and Errors

# These remain unchanged so we simply import them into this namespace.

transactional = db.transactional
Error = db.Error
BadValueError = db.BadValueError
BadPropertyError = db.BadPropertyError
BadRequestError = db.BadRequestError
EntityNotFoundError = db.EntityNotFoundError
BadArgumentError = db.BadArgumentError
QueryNotFoundError = db.QueryNotFoundError
TransactionNotFoundError = db.TransactionNotFoundError
Rollback = db.Rollback
TransactionFailedError = db.TransactionFailedError
BadFilterError = db.BadFilterError
BadQueryError = db.BadQueryError
BadKeyError = db.BadKeyError
InternalError = db.InternalError
NeedIndexError = db.NeedIndexError
ReferencePropertyResolveError = db.ReferencePropertyResolveError
Timeout = db.Timeout
CommittedButStillApplying = db.CommittedButStillApplying
ValidationError = db.ValidationError

Key = db.Key
Category = db.Category
Link = db.Link
Email = db.Email
GeoPt = db.GeoPt
IM = db.IM
PhoneNumber = db.PhoneNumber
PostalAddress = db.PostalAddress
Rating = db.Rating
Text = db.Text
Blob = db.Blob
ByteString = db.ByteString
BlobKey = db.BlobKey

NotSavedError = db.NotSavedError
KindError = db.KindError
PropertyError = db.PropertyError
DuplicatePropertyError = db.DuplicatePropertyError
ConfigurationError = db.ConfigurationError
ReservedWordError = db.ReservedWordError
DerivedPropertyError = db.DerivedPropertyError

Query = db.Query
get = db.get


### Help Function

# As a consequence of allowing string class specifiers for
# ReferenceProperty and ReverseReferenceProperty we must provide a
# PolyModel aware replacement for db.class_for_kind. We attempt to
# handle PolyModels first before falling back on to
# db.class_for_kind
def class_for_kind(kind):
  for t in polymodel._class_map.keys():
      if kind == t[-1]:
        return polymodel._class_map[t]
  try:
    return db._kind_map[kind]
  except KeyError:
    raise KindError('No implementation for kind \'%s\'' % kind)


### Properties

# Since Python is duck-typed, there's really no reason to change the
# implementation of db.Property even though we are adding `as_json` to
# all of its subclasses.  We add it here to mirror the original
# definition.
Property = db.Property

# We change the other core properties by simply subclassing them with
# the same name in a different namespace.  This makes them drop-in
# replacements for the original properties but they also have the new
# `as_json` method.

# Additionally we add from_json to each property which completes our
# support for importing and exporting JSON from models.

## Primitive Properties

class StringProperty(db.StringProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return str(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, value)


class BooleanProperty(db.BooleanProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return bool(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, value)

class IntegerProperty(db.IntegerProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return long(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, value)

class FloatProperty(db.FloatProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return float(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, value)

class TextProperty(db.TextProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return str(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, value)


## Temporal

# There is no standard for date representation in JSON.  We use
# ISO8601 for representing time which is pretty common.

# JSON.stringify(new Date()) -> 2012-04-06T19:36:35.716Z
# dateutil.parser.parse("2012-04-06T19:36:35.716Z")

class DateTimeProperty(db.DateTimeProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return value.isoformat("T") + "+00:00"

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    if value is not None:
      value = dateutil.parser.parse(value)
    setattr(model_instance, attr_name, value)

class DateProperty(db.DateProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return value.isoformat("T") + "+00:00"

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    if value is not None:
      value = dateutil.parser.parse(value)
      value = value.date()
    setattr(model_instance, attr_name, value)

class TimeProperty(db.TimeProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return value.isoformat("T") + "+00:00"

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    if value is not None:
      value = dateutil.parser.parse(value)
      value = value.time()
    setattr(model_instance, attr_name, value)


## Binary data

class ByteStringProperty(db.ByteStringProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    encoded = base64.urlsafe_b64encode(value)
    return saxutils.escape(encoded)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, value)

class BlobProperty(db.BlobProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    encoded = base64.urlsafe_b64encode(value)
    return saxutils.escape(encoded)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, value)

class BlobReferenceProperty(blobstore.BlobReferenceProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      blob_info = getattr(model_instance, self.name)

      if blob_info is None: return None

      return {
        'id': str(blob_info.key()),
        'content_type': blob_info.content_type,
        'creation': blob_info.creation.isoformat("T") + "+00:00",
        'filename': blob_info.filename,
        'size': blob_info.size}

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name

    if value == '': value = None

    # If there is an id in this struct then its output from our
    # as_json() above.
    # TODO: use isinstance
    if type(value) is dict and 'id' in value:
      setattr(model_instance, attr_name, value['id'])
    else:
      setattr(model_instance, attr_name, value)


## Special Google Data Protocol, GeoRSS GML Properties, and Atom

# GeoPtProperty
# A geographical point represented by floating-point latitude and
# longitude coordinates (Google says: In XML, this is a
# georss:point element):
#
# <gml:Point>
#   <gml:pos>45.256 -71.92</gml:pos>
# </gml:Point>
class GeoPtProperty(db.GeoPtProperty):

  # Return a GeoPt as JSON with the following form:
  #  {lat: 45.256, -71.92}
  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return {'lat': value.lat, 'lon': value.lon}

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    # TODO: we should handle the single string case: '13.42,42.13'
    setattr(model_instance, attr_name, GeoPt(value['lat'], value['lon']))

# PostalAddressProperty
# A postal address. This is a subclass of the built-in unicode type
# (Google says: In XML, this is a gd:postalAddress element):
#
# <gd:postalAddress>
#   500 West 45th Street
#   New York, NY 10036
# </gd:postalAddress>
class PostalAddressProperty(db.PostalAddressProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return str(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, PostalAddress(value))

# PhoneNumberProperty
# A human-readable telephone number. This is a subclass of the
# built-in unicode type (In XML, this is a gd.phoneNumber
# element):
#
# <gd:phoneNumber>(425) 555-8080 ext. 72585</gd:phoneNumber>
class PhoneNumberProperty(db.PhoneNumberProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return str(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, PhoneNumber(value))

# EmailProperty
# An email address. Neither the property class nor the value class
# perform validation of email addresses, they just store the
# value (In XML, this is a gd:email element):
#
# <gd:email address="foo@bar.example.com"/>
class EmailProperty(db.EmailProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return str(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    if value is None or value == "":
      #Make sure we can set this value to None.
      setattr(model_instance, attr_name, None)
    else:
      setattr(model_instance, attr_name, Email(value))

# IMProperty
# An instant messaging handle. protocol is the canonical URL of
# the instant messaging service. address is the handle's address.
# In XML, this is a gd:im element:
#
# <gd:im protocol="http://schemas.google.com/g/2005#MSN"
#        address="foo@bar.msn.com"
#        rel="http://schemas.google.com/g/2005#home"
#        primary="true"/>
class IMProperty(db.IMProperty):

  # Return an IM as JSON with the following form:
  #  {protocol: msn.com, address: 'foo@bar.msn.com'}
  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return {'protocol': value.protocol, 'address': value.address}

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    # TODO: we should handle the single string case: 'http:aim.com dlynch'
    setattr(model_instance, attr_name,
            IM(value['protocol'], value['address']))

# LinkProperty
# A fully qualified URL. This is a subclass of the built-in
# unicode type. In XML, this is an Atom Link element:
#
# <link href="http://www.google.com/" />
class LinkProperty(db.LinkProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return str(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, Link(value))

# CategoryProperty
# A category or "tag". This is a subclass of the built-in unicode
# type. In XML, this is an Atom Category element:
#
# <category term="kittens" />
class CategoryProperty(db.CategoryProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return str(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, Category(value))

# RatingProperty
# A user-provided rating for a piece of content, as an integer
# between 0 and 100. This is a subclass of the built-in long
# type. The class validates that the value is an integer between 0
# and 100, and raises a BadValueError if the value is invalid.
# In XML, this is a gd:rating element:
#
# <gd:rating value="4" />
class RatingProperty(db.RatingProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return long(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, Rating(value))

## Special User Property

# UserProperty
# A user with a Google account. A User value in the datastore does
# not get updated if the user changes her email address. This may
# be remedied in a future release. Until then, you can use the
# User value's user_id() as the user's stable unique identifier.
# nickname()
# email()
# user_id()
# federated_identity()
# federated_provider()
class UserProperty(db.UserProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return {"nickname": value.nickname(),
            "email": value.email(),
            "user_id": value.user_id(),
            "federated_identity": value.federated_identity(),
            "federated_provider": value.federated_provider()}

  # def from_json(self, model_instance, value, attr_name=None):
  #   if attr_name is None: attr_name = self.name
  #   setattr(model_instance, attr_name, value)


### ReferenceProperty

# The `ReferenceProperty` likewise has a simple `as_json` method
# similar to the properties we defined above, but I'm taking this
# opportunity to fix one of GAE's misfeatures.  When you create a
# reference in GAE it creates a backreference in the referenced
# class. It's this kind of thing that is exactly what I hate about
# Rails. It represents bad code in so many ways:
#
# * The name of the reference is not in the class that gets it which
#   violates the principal of structural locality. If we defined all
#   objects like this it would be a mess.
# * It's added wether you use it or not.  If we could refactor these
#   out, we would.  But we can't.  Unused code is a liability.
# * Auto-generated names can conflict - meaning you have to deal with
#   these reverse references even if you don't want them and you never
#   use them.
#
# GAE's model system is very much based on Django's but Google left
# out an important Django feature.  The equivalent of
# ReferenceProperties in Django can have string class specifiers.
# This is huge because Python can't deal with circular imports and
# thus circular references are impossible to implement.  We accomplish
# this by resolving the reference class later and look up the
# reference class as needed.
class ReferenceProperty(db.ReferenceProperty):

  def __init__(self,
               reference_class=None,
               verbose_name=None,
               **attrs):
    super(db.ReferenceProperty, self).__init__(verbose_name, **attrs)

    if reference_class is None:
      reference_class = Model

    self.reference_class = reference_class

  def __property_config__(self, model_class, property_name):
    super(db.ReferenceProperty, self).__property_config__(model_class,
                                                          property_name)

    if self.reference_class is db._SELF_REFERENCE:
      self.reference_class = model_class

  def validate(self, value):
    if isinstance(value, datastore.Key):
      return value

    if isinstance(value, str):
      return datastore.Key(value)

    if value is not None and not value.has_key():
      raise BadValueError(
          '%s instance must have a complete key before it can be stored as a '
          'reference' % self.reference_class.kind())

    value = super(db.ReferenceProperty, self).validate(value)

    if isinstance(self.reference_class, basestring):
      try:
        self.reference_class = class_for_kind(self.reference_class)
      except KindError:
        raise KindError('Property has undefined class type %s' %
                        (self.reference_class))

    if not ((isinstance(self.reference_class, type) and
             issubclass(self.reference_class, Model)) or
            self.reference_class is db._SELF_REFERENCE):
        raise KindError('reference_class must be Model or _SELF_REFERENCE')

    if value is not None and not isinstance(value, self.reference_class):
      raise KindError('Property %s must be an instance of %s' %
                            ("", self.reference_class.kind()))

    return value

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return None

    return str(value)

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    if value is None:
      setattr(model_instance, attr_name, None)
    elif type(value) is dict and 'id' in value:
      #If there is an id in this struct then we know what you meant.
      # TODO: use isinstance
      setattr(model_instance, attr_name, Key(value['id']))
    else:
      setattr(model_instance, attr_name, Key(value))


### ReverseReferenceProperty

# Although I hate autogenerated reverse references, reverse references
# themselves are pretty useful and so we make this class public and
# add support for string reference class specifiers.
#
# We've also added a polymorphic option that limits the collection of
# model instances returned to the specified model and its descendants.
# The original code counterintuitively returns siblings of the
# specified model along with descendants.
#
# Note that we derive ReverseReferenceProperty from object to avoid
# being detected as a property. The original code avoids this by
# binding the property later.
class ReverseReferenceProperty(object):

  def __init__(self,
               model,
               prop,
               polymorphic=None):
    self.__model = model
    self.__property = prop
    self.__polymorphic = polymorphic

  @property
  def _model(self):
    """Internal helper to access the model class, read-only."""
    if isinstance(self.__model, basestring):
        self.__model = class_for_kind(self.__model)
    return self.__model

  @property
  def _prop_name(self):
    """Internal helper to access the property name, read-only."""
    return self.__property

  @property
  def _polymorphic(self):
    """Internal helper to access polymorphic option, read-only."""
    return self.__polymorphic

  def __get__(self, model_instance, model_class):
    if model_instance is not None:
      query = Query(self._model)
      query.filter(self._prop_name + ' =', model_instance.key())
      if self._polymorphic is not None:
        query.filter(polymodel._CLASS_KEY_PROPERTY + ' =',
                     self._model.class_name())
      return query
    else:
      return self

  def __property_config__(self, model_class, attr_name):
      pass


### SelfReferenceProperty
def SelfReferenceProperty(verbose_name=None, **attrs):
    if 'reference_class' in attrs:
        raise ConfigurationError(
            'Do not provide reference_class to self-reference.')
    if 'collection_name' in attrs:
        raise ConfigurationError(
            'Do not provide collection_name to self-reference'
            ' when using Mora.')
    return ReferenceProperty(db._SELF_REFERENCE,
                             verbose_name,
                             **attrs)


### Computed Properties

# We provide a replacement for GAE's `ComputedProperty` that differs
# from the original in a few ways.  First, we have seperated the class
# from the decorator so that the decorator can take arguments.  These
# arguments allow us to set a return type to associate with the
# property.  And second, we have added an `as_json` method that uses
# this type to produce an appropriate representation for the JSON
# encoder.
class ComputedProperty(db.Property):

  def __init__(self, value_function, kind, name, indexed=True):
      super(ComputedProperty, self).__init__(indexed=indexed)
      self.__value_function = value_function
      self._kind = kind
      self._name = name

  def __set__(self, *args):
      raise db.DerivedPropertyError(
          'Computed property %s cannot be set.' % self.name)

  def __get__(self, model_instance, model_class):
      if model_instance is None:
          return self
      return self.__value_function(model_instance)

  def as_json(self, model_instance):
      value = self.__get__(model_instance, None)
      return self._kind.as_json(model_instance, value=value)

  def from_json(self, model_instance, value, attr_name=None):
      pass

# We use a decorator class to return a `ComputedProperty`.  Python's
# documentation on how this sort of thing works is a bit weak but
# Bruce Eckel has put together a nice [decorator tutorial][eckel] that
# demonstrates advanced decorator usage.
# [eckel]: http://www.artima.com/weblogs/viewpost.jsp?thread=240845 "Python Decorators II: Decorator Arguments"
class computed_property(object):

  def __init__(self, kind, indexed=True):
    self.kind = kind
    self.indexed = indexed

  def __call__(self, f, *args):
    return ComputedProperty(f,
                            *args,
                            kind=self.kind,
                            name=f.func_name,
                            indexed=self.indexed)


## Lists

class StringListProperty(db.StringListProperty):

  def as_json(self, model_instance, value=None):
    if value is None:
      value = self.get_value_for_datastore(model_instance)

    if value is None: return []

    return value

  def from_json(self, model_instance, value, attr_name=None):
    if attr_name is None: attr_name = self.name
    setattr(model_instance, attr_name, value)

def property_class_for_item_type(item_type):
    property_type = False

    if item_type in set([basestring, str, unicode]):
        property_type = StringProperty
    elif item_type is bool:
        property_type = BooleanProperty
    elif item_type == (int, long):
        property_type = IntegerProperty
    elif item_type is float:
        property_type = FloatProperty
    elif item_type is Key:
        property_type = ReferenceProperty
    elif item_type is datetime.datetime:
        property_type = DateTimeProperty
    elif item_type is datetime.date:
        property_type = DateProperty
    elif item_type is datetime.time:
        property_type = TimeProperty
    elif item_type is Text:
        property_type = TextProperty
    elif item_type is ByteString:
        property_type = ByteStringProperty
    elif item_type is users.User:
        property_type = UserProperty
    elif item_type is Email:
        property_type = EmailProperty
    elif item_type is Blob:
        property_type = BlobProperty
    elif item_type is BlobKey:
        property_type = BlobReferenceProperty
    elif item_type is Category:
        property_type = CategoryProperty
    elif item_type is Link:
        property_type = LinkProperty
    elif item_type is GeoPt:
        property_type = GeoPtProperty
    elif item_type is IM:
        property_type = IMProperty
    elif item_type is PhoneNumber:
        property_type = PhoneNumberProperty
    elif item_type is PostalAddress:
        property_type = PostalAddressProperty
    elif item_type is Rating:
        property_type = RatingProperty

    return property_type


class ListProperty(db.ListProperty):

  def as_json(self, model_instance, value=None):
      result = []

      if value is None:
          value = self.get_value_for_datastore(model_instance)

      if value is None: return []

      if self.item_type in (int, long):
          item_type = (int, long)
      else:
          item_type = self.item_type

      property_type = property_class_for_item_type(item_type)
      property_type = property_type()

      for i in value:
          result.append(property_type.as_json(False, i))

      return result

  def from_json(self, model_instance, value, attr_name=None):
      if attr_name is None: attr_name = self.name

      data = []

      if self.item_type in (int, long):
          item_type = (int, long)
      else:
          item_type = self.item_type

      property_type = property_class_for_item_type(item_type)
      property_type = property_type()

      for i in value:
          class Tmp():
              value = None
          obj = Tmp()
          property_type.from_json(obj, i, 'value')
          data.append(obj.value)

      setattr(model_instance, attr_name, data)

### Models

# Ideally I'd like Models to be drop in replacement in the same way
# that types are but GAE keeps a map of model names and also does a
# several special checks such that db.Model acts differently than its
# subclasses. Building pluggable replacements is therefore difficult.
# Instead, we let Model be db.Model and then we define our own variants.
Model = db.Model

# Our model variations have a lot of shared functionality that we push
# into a mixin.
class ModelMixin(object):

    def _json_dumps(self, obj):
        return json.dumps(obj)

    def _to_json(self, options={}, include=None, exclude=None):
        return json.dumps(self.as_json(options=options,
                                       include=include,
                                       exclude=exclude))

    # This returns representation of the model as a JSON string.
    def to_json(self, options={}, include=None, exclude=None):
        return self._to_json(options, include, exclude)

    # Most of the clever stuff happens here.  We iterate through the
    # properties checking them against the properties we should expose
    # (via `include` and `exclude`).  We then call the individual
    # properties' `as_json` methods to build the final representation.
    def _as_json(self, options={}, include=None, exclude=None):
        result = {}
        available_properties = self.properties()
        if include:
            properties = include
        else:
            properties = self.properties().keys()
            if exclude:
                for x in exclude:
                    properties.remove(x)
        for p in properties:
            if p[0:1] == "_":
                continue
            if p in available_properties:
                p_kind = self.properties()[p]
                result[p] = p_kind.as_json(self)
        return result

    # Since overriding `as_json` is pretty common and calling super
    # class methods is a pain in Python, we put the core behavior in
    # `_as_json`.
    #
    # This builds a representation of the model as a Python 'dict' that
    # can be converted to JSON.
    def as_json(self, options={}, include=None, exclude=None):
        return self._as_json(options, include, exclude)

    # Likewise we can extract a representation from json. TODO.
    def _from_json(self, data, options={}, include=None, exclude=None):
        available_properties = self.properties()
        if include:
            properties = include
        else:
            properties = self.properties().keys()
            if exclude:
                for x in exclude:
                    properties.remove(x)
        for p in properties:
            if p in available_properties:
                if p in data:
                    p_kind = self.properties()[p]
                    p_kind.from_json(self, data[p])
        self.put()

    def from_json(self, data, options={}, include=None, exclude=None):
        return self._from_json(data, options, include, exclude)


### MoraModel
# We use our mixin to define Mora's base model.
class MoraModel(db.Model, ModelMixin):

    @computed_property(StringProperty(default=""))
    def id(self):
        if self.is_saved():
            return str(self.key())
        return ""

    # We also add the method class_name to our base model to mirror
    # the class_name method in Google's PolyModel class.
    @classmethod
    def class_name(cls):
        return cls.kind()


# TODO: Do we need to replicate the App Engine PolyModel code with its
# metaclass voodoo or is there a simpler way to have kind() behave
# like it does for a vanilla App Engine PolyModel?

### MoraPolyModel
# And we also use our mixin to define Mora's base polymodel.
class MoraPolyModel(polymodel.PolyModel, ModelMixin):

    @computed_property(StringProperty(default=""))
    def id(self):
        if self.is_saved():
            return str(self.key())
        return ""

    # We also add the method class_name here to mirror the class_name
    # method in Google's PolyModel class.
    @classmethod
    def class_name(cls):
        return cls.__name__


def create(model):
    _class = db.class_for_kind(model)
    return _class()
