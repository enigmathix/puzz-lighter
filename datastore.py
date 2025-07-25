#
# This file contains the classes definining the datastore schema
#
from google.appengine.ext import ndb
from google.appengine.api import memcache
from flask_login import UserMixin
from main import loginManager

GUEST = 'guest'

#
# memcache with a prefix (e.g. for cached queries)
#
class MemCache:
	def __init__(self, prefix):
		self.prefix = prefix

	def get(self, key):
		return memcache.get(self.prefix+key)

	def set(self, key, value):
		return memcache.set(self.prefix+key, value)

	def delete(self, key):
		return memcache.delete(self.prefix+key)

#
# memcache version of ndbm
#
class MemCacheNdb(ndb.Model):
	@classmethod
	def load(cls, id, parent=None):
		key = f'{cls.__name__}/{id}'
		entity = memcache.get(key)

		if entity is not None:
			return entity

		entity = cls.get_by_id(id, parent)

		if entity:
			memcache.set(key, entity)

		return entity

	def save(self):
		self.put()
		memcache.set(f'{self.__class__.__name__}/{self.key.string_id()}', self)

	def delete(self):
		self.key.delete()
		memcache.delete(f'{self.__class__.__name__}/{self.key.string_id()}')

#
# Team
# key is team login key in hunt namespace
# unlocked is a dictionary with key a round slug and value a timestamp
# unsolved is a dictionary with key a puzzle slug and value a dictionary:
#		with key a guess and value is timestamp
# solved is a dictionary with key a puzzle slug and value the answer
# milestones is a dictionary with key a puzzle slug and value a dictionary:
#		with key the answer and value True
#
class Team(UserMixin, MemCacheNdb):
	name = ndb.StringProperty(indexed=True)
	email = ndb.StringProperty(indexed=True)
	visible = ndb.BooleanProperty(indexed=True)
	spoiled = ndb.BooleanProperty(indexed=False)
	testsolver = ndb.BooleanProperty(indexed=False)
	unlocked = ndb.JsonProperty(indexed=False, default={})
	unsolved = ndb.JsonProperty(indexed=False, default={})
	solved = ndb.JsonProperty(indexed=False, default={})
	milestones = ndb.JsonProperty(indexed=False, default={})
	lastSolve = ndb.DateTimeProperty(indexed=False)
	finishTime = ndb.DateTimeProperty(indexed=False)

	@property
	def guest(self):
		return self.key.string_id() == GUEST

	# this is used by UserMixin
	def get_id(self):
		return self.key.string_id()

#
# team loader for loginManager, use memcache to optimize datastore access
#
@loginManager.user_loader
def loadTeam(teamKey):
	if teamKey == GUEST:
		# values are set for the register page if guest decides to register
		return Team(id=GUEST, name='', email='', visible=True, spoiled=True)

	return Team.load(teamKey)

#
# Hunt
# key is hunt slug
#
class Hunt(MemCacheNdb):
	name = ndb.StringProperty(indexed=False)
	startTime = ndb.DateTimeProperty(indexed=False)
	endTime = ndb.DateTimeProperty(indexed=False)

#
# Parent for rounds and puzzles to guarantee strong consistency
# Without this inheritance, a query might not pick up the object that was
# just created (creation is done in the background for efficiency)
#
class Parent(ndb.Model):
	pass

#
#
# Round
# key is round slug in hunt namespace
#
class Round(MemCacheNdb):
	order = ndb.IntegerProperty(indexed=True)
	name = ndb.StringProperty(indexed=False)
	unlockTime = ndb.DateTimeProperty(indexed=False)
	unlockPuzzles = ndb.StringProperty(repeated=True, indexed=False)

#
# Puzzle
# key is puzzle slug in hunt namespace
# answers is a dictionary with key being the expected answers and value a dictionary:
#	final: True if this the final answer,
#			False if it's a milestone ("keep going!")
#	message: string to be shown to solver, in the checker and on the page
#	tokens: optional, a dictionary used to provide tokens to the solver,
#			format is open and used in templates
#	banner: optional, True if milestone should be shown in the template banner
#						False otherwise (default value)
#	
# errata is a dictionary with key being a timestamp and value a text
#
class Puzzle(MemCacheNdb):
	round = ndb.StringProperty(indexed=True)
	order = ndb.IntegerProperty(indexed=True)
	name = ndb.StringProperty(indexed=False)
	meta = ndb.BooleanProperty(indexed=False)
	metameta = ndb.BooleanProperty(indexed=False)
	answers = ndb.JsonProperty(indexed=False, default={})
	unlockTime = ndb.DateTimeProperty(indexed=False)
	unlockPuzzleCount = ndb.IntegerProperty(indexed=False)
	unlockPuzzles = ndb.StringProperty(repeated=True, indexed=False)
	errata = ndb.JsonProperty(indexed=False)

#
# Stats
# key is puzzle slug in hunt namespace
# stats are not part of puzzles to minimize the amount of data being sent to
# the datastore
#
class Stats(MemCacheNdb):
	solved = ndb.IntegerProperty(indexed=False, default=0)
	failed = ndb.IntegerProperty(indexed=False, default=0)
