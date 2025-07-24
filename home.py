from flask import Blueprint, request, make_response, render_template, redirect, flash
from flask_login import login_required, current_user
from google.appengine.api import mail
from common import *
from datastore import *

blueprint = Blueprint('home', __name__)

#
# Generic template display, custom is for hunt specific pages
#
def menuSelection(menu, custom=False):
	try:
		templateValues = {
			'title': f'{g.huntSlug}/title.html',
			'menu': {
				menu: 'active',
			},
		}

		path = f'/{menu}.html'

		if custom:
			path = g.huntSlug + path

		return make_response(render_template(path, **templateValues))
	except Exception as e:
		return errorPage(e)

#
# Home
#
@blueprint.route('/', methods=['GET'])
@getHunt
def home():
	return menuSelection('home', True)

#
# Details
#
@blueprint.route('/details', methods=['GET'])
@getHunt
def details():
	return menuSelection('details', True)

#
# Acknowledgments
#
@blueprint.route('/acknowledgments', methods=['GET'])
@getHunt
def acknowledgments():
	return menuSelection('acknowledgments', True)

#
# Errata
#
@blueprint.route('/errata', methods=['GET', 'POST'])
@getHunt
@login_required
def errata():
	try:
		if not g.huntStarted and not current_user.testsolver:
			return errorPage()

		if current_user.guest:
			return errorPage()

		if request.method == 'POST':
			# someone submitted an erratum
			puzzleSlug = request.form.get('puzzle')
			erratum = request.form.get('erratum')

			if g.admin:
				# for admin, update puzzle with erratum
				puzzle = Puzzle.load(puzzleSlug, parent=g.parent)

				if not puzzle:
					flash('Puzzle not found.', 'error')
					return redirect(f'/errata', 302)

				if not puzzle.errata:
					puzzle.errata = {}

				puzzle.errata[g.now.timestamp()] = erratum
				puzzle.save()

				querycache.delete(puzzle.round)

				return redirect(f'/puzzle/{puzzleSlug}', 302)
			else:
				# for users, send an email
				email = current_user.email or os.getenv("GCLOUD_EMAIL_ADDRESS")

				mail.send_mail(
					sender=f'{current_user.name} <{os.getenv("GCLOUD_EMAIL_ADDRESS")}>',
					to=f'<{os.getenv("EMAIL_ADDRESS")}>',
					reply_to=f'{current_user.name} <{email}>',
					subject='Erratum Submission',
					body=f'Team {current_user.name} submitted an erratum for {request.host_url}/puzzle/{puzzleSlug}:\n\n{erratum}')

				flash('Thank you for your submission! An erratum will be published if applicable.', 'success')
			return redirect(f'/errata', 302)

		erratables = {}
		errata = {}

		# display errata only for unlocked puzzles (puzzle title could be a spoiler)
		for roundSlug in current_user.unlocked.keys():
			if not roundSlug:
				continue

			roundPuzzles = g.hunt.puzzles[roundSlug]

			solvedCount = sum(1 for p in roundPuzzles if p.key.string_id() in current_user.solved)

			for puzzle in roundPuzzles:
				puzzleUnlocked = False

				if puzzle.unlockPuzzles:
					if set(puzzle.unlockPuzzles).issubset(current_user.solved):
						puzzleUnlocked = True
				elif not puzzle.unlockPuzzleCount or puzzle.unlockPuzzleCount <= solvedCount:
					puzzleUnlocked = True

				if puzzleUnlocked:
					erratables[puzzle.key.string_id()] = puzzle.name

					if puzzle.errata:
						for time, text in puzzle.errata.items():
							errata[time] = { 'slug': puzzle.key.string_id(),
											'name': puzzle.name,
											'text': text
											}

		templateValues = {
			'title': f'{g.huntSlug}/title.html',
			'puzzles': sorted(erratables.items(), key=lambda item: item[1]),
			'errata': dict(sorted(errata.items())),
			'menu': {
				'errata': 'active',
			},
		}

		return make_response(render_template('/errata.html', **templateValues))
	except Exception as e:
		return errorPage(e)

#
# Archive
#
@blueprint.route('/hunts', methods=['GET'])
@getHunt
def hunts():
	return menuSelection('hunts')

