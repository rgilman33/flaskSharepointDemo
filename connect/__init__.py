# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.

from connect.config import client_id, client_secret
from connect.graph_service import call_sendMail_endpoint
from flask import Flask, redirect, url_for, session, request, jsonify, render_template
from flask_oauthlib.client import OAuth, OAuthException
import json, requests, datetime
from logging import Logger
import uuid, jinja2
import pandas as pd

app = Flask(__name__)
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

"""
def _filter(s):
    return s[::-1]
app.jinja_env.filters['reverse'] = reverse_filter
"""

_js_escapes = {
        '\\': '\\u005C',
        '\'': '\\u0027',
        '"': '\\u0022',
        '>': '\\u003E',
        '<': '\\u003C',
        '&': '\\u0026',
        '=': '\\u003D',
        '-': '\\u002D',
        ';': '\\u003B',
        u'\u2028': '\\u2028',
        u'\u2029': '\\u2029'
}
# Escape every ASCII character with a value less than 32.
_js_escapes.update(('%c' % z, '\\u%04X' % z) for z in range(32))
def jinja2_escapejs_filter(value):
        retval = []
        for letter in value:
                if letter in _js_escapes:
                        retval.append(_js_escapes[letter])
                else:
                        retval.append(letter)

        return jinja2.Markup("".join(retval))

app.jinja_env.filters['escapejs'] = jinja2_escapejs_filter

# Put your consumer key and consumer secret into a config file
# and don't check it into github!!
microsoft = oauth.remote_app(
	'microsoft',
	consumer_key=client_id,
	consumer_secret=client_secret,
	request_token_params={'scope': 'User.Read Mail.Send Files.ReadWrite.All Sites.ReadWrite.All Directory.ReadWrite.All'},
	base_url='https://graph.microsoft.com/v1.0/',
	request_token_url=None,
	access_token_method='POST',
	access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
	authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
)


@app.route('/')
def index():
	 return render_template('connect.html')


@app.route('/login')
def login():
	print("logging in")

	# Generate the guid to only accept initiated logins
	guid = uuid.uuid4()
	session['state'] = guid

	return microsoft.authorize(callback=url_for('authorized', _external=True), state=guid)

@app.route('/logout')
def logout():
	session.pop('microsoft_token', None)
	session.pop('state', None)
	return redirect(url_for('index'))

@app.route('/login/authorized')
def authorized():

	print("authorizing")
	response = microsoft.authorized_response()

	if response is None:
		return "Access Denied: Reason=%s\nError=%s" % (
			request.args['error'], 
			request.args['error_description']
		)

	# Check response for state
	if str(session['state']) != str(request.args['state']):
		raise Exception('State has been messed with, end authentication')
	# Remove state session variable to prevent reuse.
	session['state'] = ""
		
	# Okay to store this in a local variable, encrypt if it's going to client
	# machine or database. Treat as a password. 
	session['microsoft_token'] = (response['access_token'], '')
	# Store the token in another session variable for easy access
	session['access_token'] = response['access_token']
	meResponse = microsoft.get('me')
	meData = json.dumps(meResponse.data)
	me = json.loads(meData)
	userName = me['displayName']
	userEmailAddress = me['userPrincipalName']
	session['alias'] = userName
	session['userEmailAddress'] = userEmailAddress
	return redirect('main')

@app.route('/main')
def main():
	if session['alias']:
		userName = session['alias']
		userEmailAddress = session['userEmailAddress']
		return render_template('main.html', alias = userName, emailAddress=userEmailAddress)
	else:
		return render_template('main.html')	

@app.route('/bars')
def bars():
	graph_api_endpoint_beta = 'https://graph.microsoft.com/beta{0}' #shit glad this works

	print_list_items_url = graph_api_endpoint_beta.format('/sharePoint/sites/e8bce531-006e-4616-9323-bfd5cce530b8,e742cb1f-7b06-497f-82a0-a237f529cb03/lists/93bb083c-d37b-46b5-b0d6-8e5dde28a697/items?expand=columnSet')

	# Set request headers.
	headers = { 
		'User-Agent' : 'python_tutorial/1.0',
		'Authorization' : 'Bearer {0}'.format(session['access_token']),
		'Accept' : 'application/json',
		'Content-Type' : 'application/json'
	}
						
	# Use these headers to instrument calls. Makes it easier
	# to correlate requests and responses in case of problems
	# and is a recommended best practice.
	request_id = str(uuid.uuid4())
	instrumentation = { 
		'client-request-id' : request_id,
		'return-client-request-id' : 'true' 
	}
	headers.update(instrumentation)

	response = requests.get(url=print_list_items_url, headers= headers, verify=False, params = None)

	d = json.loads(response.text)

	ships=[]
	preys=[]
	bas = []
	dates = []
	v = d['value']
	for i in range(len(v)):
	    c = v[i]['columnSet']
	    ship = c['Ship']
	    prey = c['Prey']
	    bootyAmount = c['bootyAmount']
	    date = datetime.datetime.strptime(c['Title'], "%Y-%m-%d")
	    #date = c['Title']
	    ships.append(ship)
	    preys.append(prey)
	    dates.append(date)
	    bas.append(bootyAmount)
	    
	df=pd.DataFrame({'Ship':ships, 'Prey':preys, 'bootyAmount':bas, 'Date':dates}).sort_values('Date', ascending=True)
	df_json = df.to_json(orient="records")
	#jd = json.dumps(json.loads(df_json))

	return render_template('bars.html', df=df_json)

# Send an email with the Microsoft Graph API.
@app.route('/send_mail')
def send_mail():
  # Change the stored email address to whatever the user put in the form.
  emailAddress = request.args.get('emailAddress')
  response = call_sendMail_endpoint(session['access_token'], session['alias'], emailAddress)
  
  # The success code for /me/sendMail is 202. Check to make sure
  # that the operation completed successfully. 
  if response == 202:
    showSuccess = 'true'  
    showError = 'false'  
  else:
    print(response)
    showSuccess = 'false' 
    showError = 'true' 
  
  session['pageRefresh'] = 'false'
  return render_template('main.html', alias=session['alias'], emailAddress=emailAddress, showSuccess=showSuccess, showError=showError)


# If library is having trouble with refresh, uncomment below and implement refresh handler
# see https://github.com/lepture/flask-oauthlib/issues/160 for instructions on how to do this

# Implements refresh token logic
# @app.route('/refresh', methods=['POST'])
# def refresh():

@microsoft.tokengetter
def get_microsoft_oauth_token():
	print("getting oauth token")
	return session.get('microsoft_token')

if __name__ == '__main__':
	app.run()
