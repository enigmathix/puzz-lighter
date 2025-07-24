from flask import Flask, current_app, request, redirect, g, make_response, render_template, session
from flask_login import LoginManager, current_user
from google.appengine.api import wrap_wsgi_app
from firebase_admin import credentials, initialize_app, db
from datetime import timedelta
import os
import json
import logging as pylogging

# server main entry point
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.wsgi_app = wrap_wsgi_app(app.wsgi_app)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=3650)
loginManager = LoginManager(app)
loginManager.login_view = 'team.register'

if os.getenv('FIREBASE_URL'):
	cert = credentials.Certificate('firebase.json')
	initialize_app(cert, {'databaseURL': os.getenv('FIREBASE_URL')})

from common import *
from datastore import *
import admin
import home
import team
import puzzle

#
# Logging filter
#
def logFilter(record):
	record.logs = json.dumps(g.logs if hasattr(g, 'logs') else {}) if current_app else ''
	return record

# redefine logging format to suit a hunt specific logger
logHandler = pylogging.StreamHandler()
logHandler.addFilter(logFilter)
pylogging.basicConfig(handlers=[logHandler], level=pylogging.INFO, format='{"payload": %(logs)s, "message": "%(message)s"}')

app.register_blueprint(admin.blueprint)
app.register_blueprint(home.blueprint)
app.register_blueprint(team.blueprint)
app.register_blueprint(puzzle.blueprint)

#
# Pre-processing of requests
#
@app.before_request
def beforeRequest():
	session.permanent = True
	g.huntSlug = getHuntSlug()
	g.hunt = {'name': 'Error'}
	g.cdn = cdn
	g.huntcdn = cdn + '/' + g.huntSlug
	g.admin = False
	g.logs = {'requestId': request.headers.get('X-Appengine-Request-Log-Id', os.getenv('X_APPENGINE_REQUEST_LOG_ID', '')),
			'resource': request.full_path,
			'ip': request.remote_addr,
			'userAgent': request.user_agent.string,
			'hunt': g.huntSlug,
			'user': '',
			'msgs': []
			}

#
# Post-processing of requests
#
@app.after_request
def afterRequest(response):
	g.logs['status'] = response.status_code

	if current_user.is_authenticated:
		g.logs['user'] = current_user.name

	pylogging.info('')
	return response

#
# Warmup
#
@app.route('/_ah/warmup')
def warmup():
	return '', 200

#
# Favicon
#
@app.route('/favicon.ico')
def favicon():
	return redirect(g.huntcdn + '/favicon.ico', code=301)

@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
@app.route('/apple-touch-icon-<int:size1>x<int:size2>.png')
@app.route('/apple-touch-icon-<int:size1>x<int:size2>-precomposed.png')
def redirect_apple_icon(size1=192, size2=192):
	return redirect(g.huntcdn + '/AppleIcon.png', code=301)

#
# Redirect to register if not logged in
#
@loginManager.unauthorized_handler
def unauthorized():
	return redirect(f'/register', 302)

#
# Handle all errors
#
@app.errorhandler(Exception)
def internalError(error):
	code = getattr(error, 'code', 500)
	return errorPage(error if code != 404 else ''), code
