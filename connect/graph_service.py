# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.

import requests
import uuid
import json
from connect.data import get_email_text

# The base URL for the Microsoft Graph API.
graph_api_endpoint = 'https://graph.microsoft.com/v1.0{0}'
graph_api_endpoint_beta = 'https://graph.microsoft.com/beta{0}' #shit glad this works

		
def call_sendMail_endpoint(access_token, alias, emailAddress):

  print("sendmail endpoint")
	# The resource URL for the sendMail action.
  send_mail_url = graph_api_endpoint.format('/me/microsoft.graph.sendMail')
  children_url = graph_api_endpoint.format('/me/drive/root/children')

  #this was for the lil test list
  #print_list_items_url = graph_api_endpoint_beta.format('/sharePoint/sites/e8bce531-006e-4616-9323-bfd5cce530b8,e742cb1f-7b06-497f-82a0-a237f529cb03/lists/5bb849ce-b10a-46f9-ac92-542e6603dedd/items?expand=columnSet')
  
  print_list_items_url = graph_api_endpoint_beta.format('/sharePoint/sites/e8bce531-006e-4616-9323-bfd5cce530b8,e742cb1f-7b06-497f-82a0-a237f529cb03/lists/93bb083c-d37b-46b5-b0d6-8e5dde28a697/items?expand=columnSet')

  drives_url = graph_api_endpoint.format('/drives')
	# Set request headers.
  headers = { 
		'User-Agent' : 'python_tutorial/1.0',
		'Authorization' : 'Bearer {0}'.format(access_token),
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
	
	# Create the email that is to be sent with API.
  email = {
		'Message': {
			'Subject': 'Welcome to Office 365 development with Python and the Office 365 Connect sample',
			'Body': {
				'ContentType': 'HTML',
				'Content': get_email_text(alias)
			},
			'ToRecipients': [
				{
					'EmailAddress': {
						'Address': emailAddress
					}
				}
			]
		},
		'SaveToSentItems': 'true'
	}   
  #url = "https://imdtester.sharepoint.com/IMDTester/_api/web/lists/getbytitle('testList')/items"

  #r = requests.GET(url=url, headers= {'Authorization': 'Bearer {0}'.format(access_token), 'accept': "application/json;odata=verbose"})

  response = requests.get(url=print_list_items_url, headers= headers, verify=False, params = None)
  #response = requests.get(url = children_url, headers = headers, verify=False, params = None)

  print(json.loads(response.text))

  #response = requests.post(url = send_mail_url, headers = headers, data = json.dumps(email), verify=False, params = None)
  

	# Check if the response is 202 (success) or not (failure).
  if (response.status_code == requests.codes.accepted):
    return response.status_code
  else:
    return "{0}: {1}".format(response.status_code, response.text)
