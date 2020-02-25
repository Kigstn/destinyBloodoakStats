import requests
from config import BUNGIE_OAUTH, BUNGIE_TOKEN, BUNGIE_SECRET, B64_SECRET
from flask import Flask, request
from database import insertToken, getRefreshToken

def refresh_token(discordID):
    url = 'https://www.bungie.net/platform/app/oauth/token/'
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'authorization': f'Basic {B64_SECRET}'
    }
    refresh_token = getRefreshToken(discordID)

    data = f'grant_type=refresh_token&refresh_token={refresh_token}'

    r = requests.post(url, data=data, headers=headers, allow_redirects=False)
    #print(r)
    data = r.json()
    access_token = data['access_token']
    refresh_token = data['refresh_token']

    insertToken(discordID, None, None, access_token, refresh_token)


########################################## FLASK STUFF ##################################################
app = Flask(__name__)


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
     

@app.route('/')
def result():
    #print('got request')
    response = request.args
    code = response['code'] #for user auth
    #print(f'code is {code}')
    (discordID,serverID) = response['state'].split(':') #mine

    url = 'https://www.bungie.net/platform/app/oauth/token/'
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'authorization': f'Basic {B64_SECRET}'
    }

    data = f'grant_type=authorization_code&code={code}'

    r = requests.post(url, data=data, headers=headers)
    #print(r)
    data = r.json()
    access_token = data['access_token']
    refresh_token = data['refresh_token']

    #print(f'bungie responded {r.content} and the token is {access_token}')
    #membershipid = r.json()['membership_id']

    reqParams = {
        'Authorization': 'Bearer ' + str(access_token),
        'X-API-Key': BUNGIE_TOKEN
    }
    
    r = requests.get(url='https://www.bungie.net/platform/User/GetMembershipsForCurrentUser/', headers=reqParams)
    response = r.json()['Response']
    membershiplist = response['destinyMemberships']
    for membership in membershiplist:
        insertToken(int(discordID), int(membership['membershipId']), int(serverID), access_token, refresh_token)
        print(discordID, ' has ID ', membership['membershipId'])
    return 'Thank you for signing up with <h1> Gravity Science </h1> !\nThere will be cake' # response to your request.

def start_server():
    if __name__ == '__main__':
        print(f'server running')
        app.run(host= '0.0.0.0',port=443, ssl_context='adhoc') #, ssl_context=context)

start_server()

