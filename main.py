import sys
import os
import logging
from functools import wraps
from flask import Flask, render_template, request, redirect, session, Response

from config import config


app = Flask(__name__)
app.secret_key = config['APP_SECRET_KEY']
app.config['SECRET_KEY'] = config['APP_SECRET_KEY']
SECRET_KEY = config['APP_SECRET_KEY']

# So it logs Flask errors to stdout - nice for Heroku logs and CI
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)


@app.before_first_request
def setup_auth_tokens():
    session['authenticated_1'] = False
    session['authenticated_2'] = False


def onefa_authorized(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session['authenticated_1']:
            return Response('You need to be authorized to view this page.',
                            401, {'WWW-Authenticate': 'Basic realm="Needs authorization."'})
        return f(*args, **kwargs)
    return wrapper


def twofa_authorized(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session['authenticated_1'] or not session['authenticated_2']:
            return Response('You need to be authorized to view this page.',
                            401, {'WWW-Authenticate': 'Basic realm="Needs authorization."'})
        return f(*args, **kwargs)
    return wrapper


@app.route('/')
def index():
    if os.environ.get('APP_CONFIG', None) == 'TestingConfig':
        session['authenticated_1'] = True
        session['authenticated_2'] = True
    if ('authenticated_1' not in session or 'authenticated_2' not in session
        or not session['authenticated_1'] or not session['authenticated_2']):
        session['authenticated_1'] = False
        session['authenticated_2'] = False
        session['random_key'] = '000000'
        return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
