# -*- coding: utf-8 -*-
#
# Copyright © 2015  Patrick Uiterwijk <patrick@puiterwijk.org>
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the GNU General Public License v2, or (at your option) any later
# version.  This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.  You
# should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

#################
# Configuration #
#################

# Groups that have "normal" access
ACC_GROUPS = ['sysadmin', 'packager', 'ambassadors']
# Groups that can mark a task as important
PRI_GROUPS = ['sysadmin-main']
# OpenID endpoint to use
OPENID_ENDPOINT = 'https://id.fedoraproject.org/'

########################
# No config below this #
########################

import os
import sys
import json
from functools import wraps
import requests
from flask.ext.fas_openid import FAS
import flask
from flask import request

if not 'API_KEY' in os.environ:
    print 'Please specify the Inthe.AM API key in the API_KEY environment variable'
    sys.exit(1)


ALL_GROUPS = set(ACC_GROUPS).union(set(PRI_GROUPS))
API_URL = 'https://inthe.am/api/v1/task/'
API_KEY = os.environ['API_KEY']
API_HEADERS = {'Authorization': 'ApiKey %s' % API_KEY}

app = flask.Flask(__name__)
app.debug = True
app.secret_key = 'FLASK:%s' % API_KEY
app.config['FAS_OPENID_ENDPOINT'] = OPENID_ENDPOINT
FAS = FAS(app)


def get_tasks():
    r = requests.get(API_URL, headers=API_HEADERS)
    print '***RESPONSE CODE: %i***' % r.status_code
    print '***RESPONSE START***'
    print r.json()['objects'][0]
    print '***RESPONSE END***'


def add_task(description, username, important):
    task = {'description': description,
            'tags': ['Submitter: %s' % username],
            'project': 'Submitted'}
    if important:
        task['priority'] = 'H'
    r = requests.post(API_URL, data=json.dumps(task), headers=API_HEADERS)
    return r.status_code


def is_authenticated():
    """ Returns wether a user is authenticated or not.
    """
    return hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None


def fas_login_required(function):
    """ Flask decorator to ensure that the user is logged in against FAS.
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):  # pragma: no cover
        """ Do the actual work of the decorator. """
        if not is_authenticated():
            return flask.redirect(flask.url_for('login'))
        return function(*args, **kwargs)
    return decorated_function


def is_in_any(needles, haystack):
    needles = set(needles)
    haystack = set(haystack)
    return needles.intersection(haystack) != []


def any_group_required(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        """ Do the actual work of the decorator. """
        if not is_authenticated():  # pragma: no cover
            return flask.redirect(flask.url_for('login'))
        elif not flask.g.fas_user.cla_done:  # pragma: no cover
            flask.flash('You must sign the CLA (Contributor License '
                        'Agreement to use tasksubmit', 'errors')
            return flask.redirect(flask.url_for('error_auth'))
        elif not is_in_any(ALL_GROUPS, flask.g.fas_user.groups):
            flask.flash('You must be in one of the groups %s' % ALL_GROUPS)
            return flask.redirect(flask.url_for('error_auth'))
        return function(*args, **kwargs)
    return decorated_function


@app.route('/', methods=['GET', 'POST'])
@any_group_required
def home():
    if request.method == 'POST':
        if 'description' not in request.form or \
                request.form['description'].strip() == '':
            flask.flash('Please enter a description')
            return flask.redirect(flask.url_for('home'))
        if 'important' in request.form and \
                not is_in_any(flask.g.fas_user.groups, PRI_GROUPS):
            flask.flash('Important is unavailable for you ' +
                        '(needs one of groups: %s)' % PRI_GROUPS)
            return flask.redirect(flask.url_for('home'))

        if add_task(request.form['description'].strip(),
                    flask.g.fas_user.username,
                    'important' in request.form) == 201:
            flask.flash('Your task has been submitted')
        else:
            flask.flash('Something went wrong adding your task')
        return flask.redirect(flask.url_for('home'))
    else:
        toreturn = '<!doctype HTML>'
        toreturn += '<html>'
        toreturn += '<head><title>Task Submitter</title></head>'
        toreturn += '<body>'
        toreturn += '<ul>'
        for message in flask.get_flashed_messages():
            toreturn += '<li>' + message + '</li>'
        toreturn += '</ul>'
        toreturn += '<form action="." method="POST">'
        toreturn += 'Submitter: <input type="text" disabled="disabled" value="%s"><br />' % flask.g.fas_user.username
        toreturn += 'Task description: <input type="text" name="description"><br />'
        if is_in_any(flask.g.fas_user.groups, PRI_GROUPS):
            toreturn += 'Important: <input type="checkbox" name="important" value="yes"><br />'
        toreturn += '<input type="submit" value="Add">'
        toreturn += '</form><br /><br />'
        toreturn += '<a href="https://github.com/puiterwijk/TaskSubmit">Open source!</a>'
        toreturn += '</body></html>'
        return toreturn


@FAS.postlogin
def check_pending_acls(return_url):  # pragma: no cover
    """ After login check if the user has ACLs awaiting review. """
    flask.session['_justlogedin'] = True
    return flask.redirect(return_url)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    next_url = flask.url_for('home')

    if hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None:
        return flask.redirect(next_url)
    else:
        return FAS.login(return_url=next_url, groups=list(ALL_GROUPS))


@app.route('/error/auth/')
def error_auth():
    return 'ERROR! You need to be authed!'

if __name__ == '__main__':
    app.run()
