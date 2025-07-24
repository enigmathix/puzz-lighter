from flask import g, request, make_response, render_template
from google.appengine.api import namespace_manager, users
from functools import wraps
from datastore import *
from datetime import datetime
import traceback
import os

# google app engine feature: GAE_ENV is localdev if it's run locally
localdev = os.getenv('GAE_ENV') == 'localdev'
cdn = '/static' if localdev else os.getenv('CDN')
domain = os.getenv('DOMAIN')
dateFmt = '%Y-%m-%dT%H:%M'
firebaseEnabled = os.getenv('FIREBASE_URL', '') != ''
querycache = MemCache(prefix='q/')

#
# Logging class, this is to format logs so they can be used by a hunt specific
# log reader
#
def gCheck(func):
	def wrapper(*args, **kwargs):
		if not hasattr(g, 'logs'):
			g.logs = {
				'requestId': os.environ.get('X_APPENGINE_REQUEST_LOG_ID', ''),
				'msgs': []
			}
		return func(*args, **kwargs)
	return wrapper

class logging:
	@gCheck
	def debug(message):
		g.logs['msgs'].append(('DEBUG', message))

	@gCheck
	def info(message):
		g.logs['msgs'].append(('INFO', message))

	@gCheck
	def warning(message):
		g.logs['msgs'].append(('WARNING', message))

	@gCheck
	def error(message):
		g.logs['msgs'].append(('ERROR', message))

	@gCheck
	def critical(message):
		g.logs['msgs'].append(('CRITICAL', message))

#
# Get hunt slug from subdomain or environment variable for local dev
#
def getHuntSlug():
	huntSlug = request.host.split('.')[0]

	if localdev:
		huntSlug = os.getenv('HUNT', '')

	return huntSlug

#
# Decorator to get hunt settings
#
def getHunt(f):
	@wraps(f)
	def parseDomain(*args, **kwargs):
		try:
			g.admin = users.is_current_user_admin()
			g.hunt = Hunt.load(g.huntSlug)

			if not g.hunt:
				logging.error(f'Hunt {g.huntSlug} not found')
				return errorPage()

			g.now = datetime.utcnow()
			g.huntStarted = (g.hunt.startTime <= g.now)
			g.huntEnded = (g.hunt.endTime < g.now)

			# this sets the namespace for all tables and memcache being accessed
			namespace_manager.set_namespace(g.huntSlug)

			g.parent = ndb.Key('Parent', g.huntSlug)
			rounds = querycache.get(g.huntSlug)

			if not rounds:
				# cache rounds query to optimize datastore access
				rounds = Round.query(ancestor=g.parent).order(Round.order).fetch(50)
				querycache.set(g.huntSlug, rounds)

			g.hunt.rounds = rounds
			g.hunt.puzzles = {}

			for round in rounds:
				roundSlug = round.key.string_id()
				puzzles = querycache.get(roundSlug)

				if not puzzles:
					# cache puzzles query to optimize datastore access
					puzzles = Puzzle.query(ancestor=g.parent).filter(Puzzle.round == roundSlug).order(Puzzle.order).fetch(100)
					querycache.set(roundSlug, puzzles)

				g.hunt.puzzles[roundSlug] = puzzles

			return f(*args, **kwargs)
		except Exception as e:
			namespace_manager.set_namespace('')
			logging.error(str(e) + traceback.format_exc())

	return parseDomain

#
# Error page
#
def errorPage(e=None):
	try:
		if e:
			logging.error(str(e) + traceback.format_exc())
			message = "Something unexpected happened, but that wasn't a puzzle."
		else:
			message = "Sorry, there's no puzzle here."

		if e and g.admin:
			message += f'<pre>{str(e)}\n{traceback.format_exc()}</pre>'

		templateValues = {
			'title': f'{g.huntSlug}/title.html',
			'menu': {
				'home': 'active',
			},
			'message': message,
		}

		logging.error(message)
		return make_response(render_template('/error.html', **templateValues))
	except Exception as e:
		logging.error(str(e) + traceback.format_exc())
		return 'This is not a puzzle 🙂', 200
