# -*- coding: utf-8 -*-
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import yaml
from flask import redirect, request, jsonify, render_template, url_for, \
    make_response, session, flash
from flask import Flask
import requests
from flask_jsonlocale import Locales
from flask_mwoauth import MWOAuth
from requests_oauthlib import OAuth1
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from pushover import Client as PushoverClient
from sseclient import SSEClient as EventSource
import json

app = Flask(__name__, static_folder='../static')

__dir__ = os.path.dirname(__file__)
app.config.update(
    yaml.safe_load(open(os.path.join(__dir__, os.environ.get(
        'FLASK_CONFIG_FILE', 'config.yaml')))))
locales = Locales(app)
_ = locales.get_message

db = SQLAlchemy(app)
migrate = Migrate(app, db)

mwoauth = MWOAuth(
    consumer_key=app.config.get('CONSUMER_KEY'),
    consumer_secret=app.config.get('CONSUMER_SECRET'),
    base_url=app.config.get('OAUTH_MWURI'),
)
app.register_blueprint(mwoauth.bp)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255))
    pushover_key = db.Column(db.String(255))

    def get_pushover_client(self):
        key = self.pushover_key

        if key is None:
            key = 'DUMMYKEY' # to return a valid client
        
        return PushoverClient(api_token=app.config.get('PUSHOVER_KEY'), user_key=key)

class StalkedPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pages = db.relationship('User', backref='pages', lazy=True, foreign_keys=[user_id])
    wiki = db.Column(db.String(255))

def logged():
    return mwoauth.get_current_user() is not None

@app.context_processor
def inject_base_variables():
    return {
        "logged": logged(),
        "username": mwoauth.get_current_user()
    }

def get_user():
    return User.query.filter_by(username=mwoauth.get_current_user()).first()

@app.before_request
def check_permissions():
    if '/login' in request.path or '/oauth-callback' in request.path:
        return

    if not logged():
        return render_template('login.html')
    
    user = get_user()
    if user is None:
        user = User(
            username=mwoauth.get_current_user()
        )
        db.session.add(user)
        db.session.commit()
    
@app.route('/', methods=['GET', 'POST'])
def index():
    user = get_user()
    if user.pushover_key is None:
        if request.method == 'GET':
            return render_template('register-pushover.html')
        
        user.pushover_key = request.form.get('key')

        c = user.get_pushover_client()
        if c.verify():
            db.session.commit()
            flash(_('register-pushover-success'))
        else:
            user.pushover_key = None
            flash(_('register-pushover-invalid-key'))

        return redirect(url_for('index'))
    
    if request.method == 'GET':
        return render_template('manage-pages.html', pages=user.pages)

    page = StalkedPage(
        user_id=user.id,
        title=request.form.get('title'),
        wiki=request.form.get('wiki').replace(' ', '_')
    )
    db.session.add(page)
    db.session.commit()
    flash(_('manage-pages-success'))
    return redirect(url_for('index'))
    
@app.cli.command('stalk-pages', help='Stalk pages')
def cli_stalk_pages():
    # load stalked pages to RAM
    stalked_pages = {}
    for page in StalkedPage.query.all():
        if page.wiki not in stalked_pages:
            stalked_pages[page.wiki] = []
        
        stalked_pages[page.wiki].append(page.title.replace(' ', '_'))
    
    stream = 'https://stream.wikimedia.org/v2/stream/recentchange'
    while True:
        try:
            for event in EventSource(stream):
                if event.event == 'message':
                    try:
                        change = json.loads(event.data)
                    except ValueError:
                        continue
                    
                    if change['wiki'] not in stalked_pages:
                        continue
                    
                    if change['type'] != 'edit':
                        continue
                    
                    if change['title'].replace(' ', '_') in stalked_pages[change['wiki']]:
                        pages = StalkedPage.query.filter_by(title=change['title'].replace(' ', '_'), wiki=change['wiki'])

                        for page in pages:
                            notification = 'User %s made an edit at "%s"@%s, edit summary "%s"' % (change['user'], change['title'], change['wiki'], change['comment'])
                            user = User.query.filter_by(id=page.user_id).first()
                            user.get_pushover_client().send_message(notification)
        except Exception as e:
            raise e

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
