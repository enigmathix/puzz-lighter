from flask import Blueprint, request, make_response, render_template, redirect, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from google.appengine.api import mail
from firebase_admin import db as firebase_db
import requests
from common import *
from datastore import *
from datetime import datetime
import secrets
import string

blueprint = Blueprint('team', __name__)

KEY_LENGTH = 10
characters = string.ascii_letters + string.digits

#
# reCAPTCHA verification
#
def checkCaptcha():
	if not os.getenv('CAPTCHA_SECRET_KEY'):
		return True

	captcha = {'response': request.form.get('g-recaptcha-response'),
			'secret': os.getenv('CAPTCHA_SECRET_KEY')}

	if not captcha['response']:
		flash('reCAPTCHA failed', 'error')
		logging.warning('reCAPTCHA missing')
		return False

	response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=captcha)

	if not response or response.status_code != 200:
		flash('reCAPTCHA failed', 'error')
		logging.warning('reCAPTCHA failed')
		return False

	return True

#
# Check team name is unique
#
def checkNameUnicity(name):
	team_id = Team.query(Team.name == name).get(keys_only=True)

	if team_id:
		if not current_user.is_authenticated or current_user.get_id() != team_id:
			return 'A team with that name already exists.'

	return False

#
# Check email address is unique
#
def checkEmailUnicity(email):
	if not email:
		return False

	team_id = Team.query(Team.email == email).get(keys_only=True)

	if team_id:
		if not current_user.is_authenticated or current_user.get_id() != team_id:
			return 'A team is already associated with this email address.'

	return False

#
# Login
#
@blueprint.route('/login', methods=['GET', 'POST'])
@getHunt
def login():
	try:
		templateValues = {
			'title': f'{g.huntSlug}/title.html',
			'menu': {
				'home': 'active',
			},
			'captcha_key': os.getenv('CAPTCHA_KEY'),
		}

		if request.method == 'GET':
			# landing page for login
			key = request.args.get('key')

			if not key:
				return make_response(render_template('/login.html', **templateValues))

			# landing page for invitation link
			team = None

			if len(key) == KEY_LENGTH or key == GUEST:
				team = Team.load(key)

			if not team:
				flash(f'Sorry, {key} is not a valid team key.', 'error')
				logging.warning(f'Invalid team key {key}')
				return make_response(render_template('/login.html', **templateValues))

			# login in flask
			login_user(team)
			session.permanent = True
			flash(f'Hello, <a href="/team">{team.name}</a>!', 'success')
			logging.info('Someone joined the team')
			return redirect('/', 302)
		else:
			# processing of key input
			key = request.form.get('new-password', '').strip()
			email = request.form.get('email', '').strip()
			team = None

			if not key and not email:
				flash('Your input must not be empty.', 'error')
				return make_response(render_template('/login.html', **templateValues))

			if not checkCaptcha():
				return make_response(render_template('/login.html', **templateValues))

			if key:
				team = Team.load(key)
			elif email:
				team = Team.query(Team.email == email).get()

			if not team:
				flash('No team could be found.', 'error')
				logging.warning(f'No team found for {key if key else email}')
				return make_response(render_template('/login.html', **templateValues))

			if key:
				# login in flask
				login_user(team)
				session.permanent = True
				flash(f'Hello, <a href="/team">{team.name}</a>!', 'success')
				logging.info('Someone joined the team')
				return redirect('/', 302)
			else:
				# send key by email
				mail.send_mail(
					sender=f'{g.hunt.name} <{os.getenv("EMAIL_ADDRESS")}>',
					to=f'<{email}>',
					subject=f'Your {g.hunt.name} Key',
					body=f'Team {team.name},\n\nYour team key is {team.key.string_id()}. you can log in by following this link: {request.base_url}?key={team.key.string_id()}\n\n{g.hunt.name}')

				flash('An email with your team key has been sent.', 'success')
				logging.info(f'Sent email to recover key {team.key.string_id()} for {email}')
				return redirect('/login', 302)
	except Exception as e:
		return errorPage(e)

#
# Register
#
@blueprint.route('/register', methods=['GET', 'POST'])
@getHunt
def register():
	try:
		templateValues = {
			'title': f'{g.huntSlug}/title.html',
			'header': 'Register Your Team',
			'menu': {
				'home': 'active',
			},
			'captcha_key': os.getenv('CAPTCHA_KEY'),
		}

		if request.method == 'GET':
			# landing page for registration, generate key so that the password
			# manager can save it
			templateValues['key'] = ''.join(secrets.choice(characters) for _ in range(KEY_LENGTH))
			return make_response(render_template('/team.html', **templateValues))
		else:
			# registration processing
			teamName = request.form.get('username').strip()
			key = request.form.get('new-password')
			email = request.form.get('email').strip()
			visible = bool(request.form.get('visible'))
			spoiled = bool(request.form.get('spoiled'))

			templateValues['key'] = key

			if not teamName:
				flash('Your team name must not be empty.', 'error')
				return make_response(render_template('/team.html', **templateValues))

			if not current_user.is_authenticated or current_user.guest:
				# new team
				if not checkCaptcha():
					return make_response(render_template('/team.html', **templateValues))

				error = checkNameUnicity(teamName)

				if error:
					flash(error, 'error')
					return make_response(render_template('/team.html', **templateValues))

				error = checkEmailUnicity(email)

				if error:
					flash(error, 'error')
					return make_response(render_template('/team.html', **templateValues))

				team = Team(id = key,
					name = teamName,
					email = email,
					visible = visible,
					spoiled = spoiled)
				team.save()

				# login in flask
				login_user(team)
				session.permanent = True
				flash(f'Hello, {team.name}!<br>Please visit <a href="/team">your profile</a> to share your key with your team.', 'success')
				logging.info('Registered')

				if firebaseEnabled:
					try:
						ref = firebase_db.reference(f'{g.huntSlug}/{key}')
						ref.set({'timestamp': {'.sv': 'timestamp'},
								'team': teamName,
								'puzzle': { 'name': '', 'slug': '' }})
					except Exception as e:
						logging.error(str(e))
						pass

				# redirect to home page, that's a browser requirement:
				# the next page must be a different one for the password manager
				# to offer to save the password
				return redirect('/', 302)
			else:
				# just saving team preferences
				if g.huntStarted and not g.huntEnded and visible and not current_user.visible:
					flash('You cannot switch from stealth mode to public mode during the hunt.', 'error')
					return redirect('/team', 302)

				if current_user.finishTime and current_user.visible and not visible:
					flash('You cannot switch to stealth mode after finishing the hunt.', 'error')
					return redirect('/team', 302)

				if teamName != current_user.name:
					error = checkNameUnicity(teamName)
					if error:
						flash(error, 'error')
						return redirect('/team', 302)

				if email != current_user.email:
					error = checkEmailUnicity(email)
					if error:
						flash(error, 'error')
						return redirect('/team', 302)

				current_user.name = teamName
				current_user.email = email
				current_user.visible = visible
				current_user.spoiled = spoiled

				if current_user.testsolver and request.form.get('reset'):
					current_user.unlocked.clear()
					current_user.unsolved.clear()
					current_user.milestones.clear()
					current_user.solved.clear()
					current_user.finishTime = None

				current_user.save()

				if firebaseEnabled:
					try:
						ref = firebase_db.reference(f'{g.huntSlug}/{current_user.get_id()}/team')
						ref.set(teamName)
					except Exception as e:
						logging.error(str(e))
						pass

			return redirect('/team', 302)
	except Exception as e:
		return errorPage(e)

#
# Guest interface
#
@blueprint.route('/guest', methods=['GET', 'POST'])
@getHunt
def guest():
	try:
		if not g.huntEnded:
			return errorPage(e)

		team = Team(id=GUEST, name='', email='', visible=True, spoiled=True)
		login_user(team)
		session.permanent = True
		flash(f'Hello, guest!<br>Feel free to check the <a href="/puzzles">puzzles</a>.', 'success')
		return redirect('/', 302)
	except Exception as e:
		return errorPage(e)

#
# Team profile
#
@blueprint.route('/team', methods=['GET'])
@getHunt
@login_required
def team():
	try:
		if current_user.guest:
			return errorPage()

		templateValues = {
			'title': f'{g.huntSlug}/title.html',
			'header': current_user.name,
			'key': current_user.get_id(),
			'keyurl': f'{request.base_url.replace("team", "login")}?key={current_user.get_id()}',
			'menu': {
				'profile': 'active',
			},
		}

		return render_template('/team.html', **templateValues)
	except Exception as e:
		return errorPage(e)

#
# Leaderboard
#
@blueprint.route('/teams', methods=['GET'])
@getHunt
def teams():
	try:
		if g.admin:
			teams = Team.query().fetch(10000)
		else:
			teams = Team.query(Team.visible == True).fetch(10000)

		templateValues = {
			'title': f'{g.huntSlug}/title.html',
			'menu': {
				'teams': 'active',
			},
			'teams': teams,
		}

		return make_response(render_template('/teams.html', **templateValues))
	except Exception as e:
		return errorPage(e)

#
# Admin interface in teams page
#
@blueprint.route('/adminteam', methods=['GET'])
@getHunt
def testsolver():
	try:
		key = request.args.get('key')
		testsolver = request.args.get('test', type=int)

		team = Team.load(key)

		if team:
			team.testsolver = True if testsolver else False
			team.save()
			return 'Team set as testsolver.' if testsolver else 'Team is no longer testsolver.', 200

		return 'Nothing was done.', 200
	except Exception as e:
		return errorPage(e)
