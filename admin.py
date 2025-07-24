from flask import Blueprint, g, request, make_response, render_template, redirect, flash
from google.appengine.api import namespace_manager
from firebase_admin import auth
import urllib.parse
from datetime import datetime
import pytz
import logging
import traceback
from common import *
from datastore import *
import importlib

blueprint = Blueprint('admin', __name__)

#
# Return list of numbered values in a form
#
def getValueList(request, field):
	values = []
	n = 1

	while True:
		value = request.values.get('%s%d' % (field, n))

		if value is None:
			break

		values.append(value)
		n += 1

	return values

#
# Convert user time to and from UTC
#
def toUTC(date, tz):
	userDate = datetime.strptime(date, dateFmt)
	userTz = pytz.timezone(tz)
	return userTz.localize(userDate).astimezone(pytz.utc)

#
# Error handling
#
def adminError(e=''):
	logging.error(str(e) + traceback.format_exc())
	templateValues = {
		'error': str(e),
		'trace': traceback.format_exc(),
	}
	flash(f'{str(e)} {traceback.format_exc()}', 'error')
	return redirect(request.referrer if request.referrer else '/admin', 302)

#
# Display admin
#
@blueprint.route('/admin', methods=['GET'])
def admin():
	try:
		g.hunt = {}
		hunts = Hunt.query().fetch(100)

		templateValues = {
			'domain': domain,
			'hunts': hunts,
		}

		if os.getenv('FIREBASE_URL'):
			templateValues['token'] = auth.create_custom_token('admin').decode('ascii')

		return make_response(render_template('admin.html', **templateValues))
	except Exception as e:
		return adminError(e)

#
# Handle hunt
#
@blueprint.route('/adminhunt', methods=['GET', 'POST'])
def adminhunt():
	try:
		if request.method == 'GET':
			g.hunt = Hunt.load(g.huntSlug)

			if not g.hunt:
				flash('Hunt not found', 'error')
				return redirect(f'/admin', 302)

			namespace_manager.set_namespace(g.huntSlug)
			g.parent = ndb.Key('Parent', g.huntSlug)
			rounds = Round.query(ancestor=g.parent).order(Round.order).fetch(50)
			puzzles = Puzzle.query(ancestor=g.parent).order().fetch(500)
			huntPuzzles = []

			for huntPuzzle in puzzles:
				# puzzles in this hunt that could unlock this round
				huntPuzzles.append({'slug': huntPuzzle.key.string_id(), 'round': huntPuzzle.round, 'order': huntPuzzle.order, 'name': huntPuzzle.name })

			templateValues = {
				'rounds': sorted(rounds, key=lambda x: x.order),
				'huntPuzzles': huntPuzzles,
				'round': {'unlockPuzzles': []},
				'roundSlug': '',
			}

			return make_response(render_template('adminhunt.html', **templateValues))
		else:
			if request.values.get('action') == 'Delete':
				hunt = Hunt.load(g.huntSlug)

				if hunt:
					hunt.delete()
				else:
					flash('Hunt not found', 'error')
					return redirect(f'/admin', 302)

				return redirect('/admin', 302)
			else:
				timezone = request.values.get('timezone')

				hunt = Hunt(id = g.huntSlug,
					name = request.values.get('name'),
					startTime = toUTC(request.values.get('startTime'), timezone).replace(tzinfo=None),
					endTime = toUTC(request.values.get('endTime'), timezone).replace(tzinfo=None),
					)
				hunt.save()

				return redirect('/adminhunt', 302)
	except Exception as e:
		return adminError(e)
	finally:
		namespace_manager.set_namespace('')

#
# Handle rounds
#
@blueprint.route('/adminround', methods=['GET', 'POST'])
@getHunt
def adminRound():
	try:
		if request.method == 'GET':
			roundSlug = request.values.get('round')
			round = Round.load(roundSlug, parent=g.parent)

			if not round:
				flash('Round not found', 'error')
				return redirect(f'/adminhunt', 302)

			puzzles = Puzzle.query(ancestor=g.parent).order(Puzzle.order).fetch(500)
			huntPuzzles = []
			roundPuzzles = {}

			for huntPuzzle in puzzles:
				puzzleSlug = huntPuzzle.key.string_id()

				# puzzles in this round
				if huntPuzzle.round == roundSlug:
					roundPuzzles[puzzleSlug] = {
						'slug': puzzleSlug,
						'order': huntPuzzle.order,
						'name': huntPuzzle.name,
						'meta': 1 if huntPuzzle.meta else 0,
					}
				else:
					# puzzles in this hunt that could unlock this round
					huntPuzzles.append({'slug': puzzleSlug, 'round': huntPuzzle.round, 'order': huntPuzzle.order, 'name': huntPuzzle.name })

			templateValues = {
				'round': round,
				'roundSlug': roundSlug,
				'huntPuzzles': huntPuzzles,
				'roundPuzzles': roundPuzzles,
				'puzzle': {'answers': {' ': {'final': True, 'message': '', 'tokens': {}}}, 'unlockPuzzles': []},
				'puzzleSlug': '',
			}

			return make_response(render_template('adminround.html', **templateValues))
		else:
			roundSlug = urllib.parse.quote(request.values.get('slug').lower())

			if request.values.get('action') == 'Delete':
				round = Round.load(roundSlug, parent=g.parent)

				if round:
					round.delete()
				else:
					flash('Round not found', 'error')
					return redirect(f'/adminhunt', 302)

				return redirect('/adminhunt', 302)
			else:
				unlockPuzzles = getValueList(request, 'unlockRoundPuzzles')

				round = Round(parent = g.parent,
					id = roundSlug,
					order = int(request.values.get('order')),
					name = request.values.get('name'),
					unlockPuzzles = unlockPuzzles,
				)

				unlockTime = request.values.get('unlockTime')
				timezone = request.values.get('timezone')

				if unlockTime:
					round.unlockTime = toUTC(unlockTime, timezone).replace(tzinfo=None)

				round.save()
				querycache.delete(g.huntSlug)

				return redirect(f'/adminround?round={roundSlug}', 302)
	except Exception as e:
		return adminError(e)

#
# Handle puzzles
#
@blueprint.route('/adminpuzzle', methods=['GET', 'POST'])
@getHunt
def adminPuzzle():
	try:
		if request.method == 'GET':
			roundSlug = request.values.get('round')
			puzzleSlug = request.values.get('puzzle')
			round = Round.load(roundSlug, parent=g.parent)

			if not round:
				flash('Round not found', 'error')
				return redirect(f'/adminhunt', 302)

			puzzle = Puzzle.load(puzzleSlug, parent=g.parent)

			if not puzzle:
				flash('Puzzle not found', 'error')
				return redirect(f'/adminround?round={roundSlug}', 302)

			puzzles = Puzzle.query(ancestor=g.parent).filter(Puzzle.round == roundSlug).order(Puzzle.order).fetch(100)
			roundPuzzles = []

			# puzzles in the round that could unlock this one
			for roundPuzzle in puzzles:
				if roundPuzzle.key.string_id() != puzzle.key.string_id():
					roundPuzzles.append({'slug': roundPuzzle.key.string_id(), 'round': roundSlug, 'order': roundPuzzle.order, 'name': roundPuzzle.name })

			templateValues = {
				'round': round,
				'puzzle': puzzle,
				'roundSlug': roundSlug,
				'puzzleSlug': puzzleSlug,
				'roundPuzzles': roundPuzzles,
			}

			return make_response(render_template('adminpuzzle.html', **templateValues))
		else:
			roundSlug = request.values.get('roundslug')
			puzzleSlug = urllib.parse.quote(request.values.get('slug').lower())

			if request.values.get('action') == 'Delete':
				puzzle = Puzzle.load(puzzleSlug, parent=g.parent)

				if puzzle:
					puzzle.delete()
				else:
					flash('Puzzle not found', 'error')
					return redirect(f'/adminround?round={roundSlug}', 302)

				return redirect(f'/adminround?round={roundSlug}', 302)
			else:
				timezone = request.values.get('timezone')
				unlockPuzzles = getValueList(request, 'unlockPuzzles')

				puzzle = Puzzle(parent = g.parent,
					id = puzzleSlug,
					round = roundSlug,
					order = int(request.values.get('order')),
					meta = True if request.values.get('meta') else False,
					metameta = True if request.values.get('metameta') else False,
					name = request.values.get('name'),
					unlockPuzzles = unlockPuzzles,
				)

				# answers
				puzzle.answers = {}
				answers = getValueList(request, 'answer')
				finals = getValueList(request, 'final')
				messages = getValueList(request, 'message')

				for i, answer in enumerate(answers):
					answer = answer.strip().lower()

					if not answer:
						flash('Answer cannot be empty', 'error')
						return redirect(request.referrer, 302)

					puzzle.answers[answer] = { 'final': finals and finals[i] == 'on',
												'message': messages[i] }
					tokenKeys = getValueList(request, 'token%dKey' % (i+1))
					tokenValues = getValueList(request, 'token%dValue' % (i+1))

					if tokenKeys and tokenValues:
						tokens = {}

						for j, tokenKey in enumerate(tokenKeys):
							tokenValue = tokenValues[j]
							if tokenKey and tokenValue:
								tokens[tokenKey] = tokenValue

						puzzle.answers[answer]['tokens'] = tokens

				# unlock
				unlockTime = request.values.get('unlockTime')

				if unlockTime:
					puzzle.unlockTime = toUTC(unlockTime, timezone).replace(tzinfo=None)

				unlockPuzzleCount = request.values.get('unlockPuzzleCount')

				if unlockPuzzleCount:
					puzzle.unlockPuzzleCount = int(unlockPuzzleCount)

				puzzle.save()
				querycache.delete(roundSlug)

				return redirect(f'/adminround?round={roundSlug}', 302)
	except Exception as e:
		return adminError(e)

#
# Handle rounds
#
@blueprint.route('/adminpopulate/<year>', methods=['GET'])
@getHunt
def adminPopulate(year):
	try:
		importlib.import_module(f'populate-{year}')

		return redirect(f'/admin', 302)
	except Exception as e:
		return adminError(e)
