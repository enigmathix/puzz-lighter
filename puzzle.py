from flask import Blueprint, request, make_response, render_template, jsonify
from flask_login import login_required, current_user
from jinja2 import TemplateNotFound
from firebase_admin import db as firebase_db
from common import *
from datastore import *
from datetime import datetime
import traceback

blueprint = Blueprint('puzzle', __name__)

# max number of guesses in the given time period
maxGuesses = 20
waitingTime = 86400

#
# Check if round is unlocked for team
#
def isRoundUnlocked(round):
	if current_user.guest:
		return True

	if round.unlockTime and not current_user.testsolver:
		if round.unlockTime > g.now:
			return False

	for puzzle in round.unlockPuzzles:
		if puzzle not in current_user.solved:
			return False

	return True

#
# Return accessible rounds and current one
#
def getRounds(roundSlug):
	currentSlug = None
	currentRound = None
	rounds = []

	for round in g.hunt.rounds:
		slug = round.key.string_id()

		if not currentRound:
			currentSlug = slug
			currentRound = round

		if isRoundUnlocked(round):
			rounds.append(round)

			if slug == roundSlug:
				currentSlug = slug
				currentRound = round

	# set round as unlocked to start timer for hints
	if not current_user.guest and currentSlug and currentSlug not in current_user.unlocked:
		current_user.unlocked[currentSlug] = g.now.timestamp()
		current_user.save()

	return currentSlug, currentRound, rounds

#
# Clean up attempts and return them with waiting time if applicable
#
def getAttempts(puzzleSlug):
	guessesLeft = maxGuesses
	delay = 0

	milestones = current_user.milestones.get(puzzleSlug, {})
	attempts = current_user.unsolved.get(puzzleSlug, {})

	if attempts:
		now = g.now.timestamp()
		dayAttempts = [time for guess, time in attempts.items() if time >= now-waitingTime]
		guessesLeft = maxGuesses - len(dayAttempts)

		# delay is calculated before the last guess is made
		if guessesLeft <= 1:
			delay = int(waitingTime + dayAttempts[0] - now)

	return list(milestones.keys()), attempts, guessesLeft, delay

#
# Puzzles in a round
#
@blueprint.route('/puzzles/<roundSlug>', methods=['GET'])
@blueprint.route('/puzzles/', methods=['GET'])
@getHunt
@login_required
def puzzles(roundSlug=''):
	try:
		if not g.huntStarted and not current_user.testsolver:
			logging.warning('Hunt not started')
			return errorPage()

		if current_user.guest and not g.huntEnded:
			logging.warning('Hunt not ended')
			return errorPage()

		roundSlug, round, rounds = getRounds(roundSlug)

		if not roundSlug:
			logging.warning('Round not found')
			return errorPage()

		puzzles = g.hunt.puzzles[roundSlug]
		unlockedPuzzles = []
		metaSolved = False
		solvedCount = sum(1 for p in puzzles if p.key.string_id() in current_user.solved)

		# find unlocked puzzles
		if current_user.guest:
			unlockedPuzzles = puzzles
		else:
			for puzzle in puzzles:
				if puzzle.meta and puzzle.key.string_id() in current_user.solved:
					metaSolved = True

				if puzzle.unlockPuzzles:
					if set(puzzle.unlockPuzzles).issubset(current_user.solved):
						unlockedPuzzles.append(puzzle)
				elif not puzzle.unlockPuzzleCount or puzzle.unlockPuzzleCount <= solvedCount:
					unlockedPuzzles.append(puzzle)

		templateValues = {
			'roundSlug': roundSlug,
			'rounds': rounds,
			'puzzles': unlockedPuzzles,
			'metaSolved': metaSolved,
			'menu': {
				'puzzles': 'active',
			},
		}

		# show stats for admin
		if g.admin:
			stats = {}

			for puzzle in puzzles:
				stats[puzzle.key.string_id()] = (0, 0)

			for stat in Stats.query().fetch(500):
				stats[stat.key.string_id()] = (stat.solved, stat.failed)

			templateValues['stats'] = stats

		return make_response(render_template(f'{g.huntSlug}/{roundSlug}.html', **templateValues))
	except Exception as e:
		return errorPage(e)

#
# Puzzle page
#
@blueprint.route('/puzzle/<puzzleSlug>', methods=['GET'])
@getHunt
@login_required
def puzzle(puzzleSlug):
	try:
		if not g.huntStarted and not current_user.testsolver:
			logging.warning('Hunt not started')
			return errorPage()

		if current_user.guest and not g.huntEnded:
			logging.warning('Hunt not ended')
			return errorPage()

		puzzle = Puzzle.load(puzzleSlug, parent=g.parent)

		if not puzzle:
			logging.warning(f'Puzzle {puzzleSlug} not found')
			return errorPage()

		roundSlug, round, rounds = getRounds(puzzle.round)

		if puzzle.round != roundSlug:
			logging.warning(f'Puzzle {puzzleSlug} does not match round {roundSlug}')
			return errorPage()

		# check if puzzle is unlocked
		if not current_user.guest:
			for slug in puzzle.unlockPuzzles:
				if slug not in current_user.solved:
					logging.warning(f'Puzzle {puzzleSlug} not unlocked')
					return errorPage()

			if puzzle.unlockPuzzleCount and puzzle.unlockPuzzleCount > sum(1 for p in g.hunt.puzzles[puzzle.round] if p.key.string_id() in current_user.solved):
				logging.warning(f'Puzzle {puzzleSlug} not unlocked, {puzzle.unlockPuzzleCount} puzzles need to be solved.')
				return errorPage()

		milestones, attempts, guessesLeft, delay = getAttempts(puzzleSlug)
		userAnswer = ''
		puzzleAnswer = ''
		message = ''
		solved = False
		solution = False	# whether to show the solution or not

		if g.huntEnded:
			solution = True

			for answer, params in puzzle.answers.items():
				if params['final']:
					puzzleAnswer = answer
					break

		if puzzleSlug in current_user.solved:
			userAnswer = current_user.solved[puzzleSlug]
			message = puzzle.answers[userAnswer]['message']
			solved = True
			solution = True

			# for metas, don't show write-up until all puzzles in the round
			# are solved
			if puzzle.meta and not g.huntEnded:
				for roundPuzzle in g.hunt.puzzles[puzzle.round]:
					if roundPuzzle.key.string_id() not in current_user.solved:
						solution = False
						break

		templateValues = {
			'rounds': rounds,
			'round': round,
			'puzzle': puzzle,
			'unlockTime': 0 if current_user.guest else current_user.unlocked[roundSlug],
			'milestones': milestones,
			'solved': solved,
			'solution': solution,
			'attempts': dict(list(attempts.items())),
			'guessesLeft': guessesLeft,
			'delay': delay,
			'userAnswer': userAnswer,
			'puzzleAnswer': puzzleAnswer,
			'message': message,
			'menu': {
				'puzzles': 'active',
			}
		}

		return make_response(render_template(f'{g.huntSlug}/{puzzleSlug}.html', **templateValues))
	except TemplateNotFound:
		return errorPage()
	except Exception as e:
		return errorPage(e)

#
# Process guess
#
@blueprint.route('/guess', methods=['POST'])
@getHunt
@login_required
def guess():
	try:
		if current_user.guest:
			return jsonify({'error': f"Guests can't guess."})

		puzzleSlug = request.json.get('puzzle')

		if puzzleSlug in current_user.solved:
			return jsonify({'error': f"Your team already solved this puzzle."})

		guess = request.json.get('guess').replace(' ', '').lower()
		response = {'guess': guess}

		_, attempts, guessesLeft, delay = getAttempts(puzzleSlug)

		if not guess:
			return jsonify({'error': f"Please enter a non-empty guess."})

		if guess in attempts:
			return jsonify({'error': f"You've already tried <i>{guess}</i>."})

		if guessesLeft <= 0:
			return jsonify({'error': f"No guess left, please wait for {delay} seconds."})

		puzzle = Puzzle.load(puzzleSlug, parent=g.parent)

		if not puzzle:
			logging.error(f'Puzzle {puzzleSlug} not found')
			return jsonify({'error': 'Puzzle  not found.'}), 404

		solved = False

		for answer, params in puzzle.answers.items():
			if guess == answer.replace(' ', ''):
				response['correct'] = True
				response['final'] = params['final']
				response['guess'] = answer
				response['message'] = params.get('message', '')

				if params['final'] == True:
					current_user.solved[puzzleSlug] = answer

					if not g.huntEnded:
						current_user.lastSolve = g.now

						if puzzle.metameta:
							current_user.finishTime = g.now

					attempts.clear()
					solved = True
					logging.info(f'Solved {puzzle.name}')
				else:
					if not puzzleSlug in current_user.milestones:
						current_user.milestones[puzzleSlug] = {}

					current_user.milestones[puzzleSlug][answer] = True
					response['banner'] = params.get('banner', False)
					response['milestones'] = list(current_user.milestones[puzzleSlug].keys())
					response['attempts'] = attempts
					response['guessesLeft'] = guessesLeft
					logging.info(f'Guessed "{answer}" correctly on {puzzle.name}')

				break
		else:
			response['correct'] = False
			logging.warning(f'Guessed "{guess}" on {puzzle.name}')

		if not response['correct']:
			attempts[guess] = g.now.timestamp()
			response['milestones'] = list(current_user.milestones.get(puzzleSlug, {}).keys())
			response['attempts'] = dict(list(attempts.items()))
			response['delay'] = delay
			response['guessesLeft'] = guessesLeft-1

			# update stats only for non testsolvers
			if not current_user.testsolver:
				stats = Stats.load(puzzleSlug)

				if not stats:
					stats = Stats(id = puzzleSlug)

				stats.failed += 1
				stats.save()

		current_user.unsolved[puzzleSlug] = attempts
		current_user.save()

		if solved:
			try:
				# update stats only for non testsolvers
				if not current_user.testsolver:
					stats = Stats.load(puzzleSlug)

					if not stats:
						stats = Stats(id = puzzleSlug)

					stats.solved += 1
					stats.save()
			except Exception as e:
				logging.error(str(e) + traceback.format_exc())

			if firebaseEnabled:
				try:
					ref = firebase_db.reference(f'{g.huntSlug}/{current_user.get_id()}')
					ref.update({'timestamp': {'.sv': 'timestamp'},
							'puzzle/name': puzzle.name,
							'puzzle/slug': puzzle.key.string_id(),
							});
				except:
					pass

		return jsonify(response)
	except Exception as e:
		logging.error(str(e) + traceback.format_exc())
		return jsonify({'error': 'An error occured.'}), 500
