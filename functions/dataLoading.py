from functions.network  import getJSONfromURL, getComponentInfoAsJSON
from static.dict        import getNameFromHashRecords, getNameFromHashCollectible, getNameFromHashActivity, getNameFromHashInventoryItem
from functions.database import db_connect, insertActivity, insertCharacter, insertInstanceDetails, updatedPlayer, getLastUpdated
from functions.database import getSystemAndChars, getLastUpdated

from concurrent.futures import ThreadPoolExecutor, as_completed

from datetime           import timedelta, datetime
from pprint             import pprint

import os
import requests
import json
import zipfile
import sqlite3

def getJSONfromRR(playerID):
    """ Gets a Players stats from the RR-API """
    requestURL = 'https://b9bv2wd97h.execute-api.us-west-2.amazonaws.com/prod/api/player/{}'.format(playerID)
    return getJSONfromURL(requestURL)

def getTriumphsJSON(playerID):
    """ returns the json containing all triumphs the player <playerID> has """
    achJSON = getComponentInfoAsJSON(playerID, 900)
    if not achJSON:
        return None
    if 'data' not in achJSON['Response']['profileRecords']:
        return None
    return achJSON['Response']['profileRecords']['data']['records']

def getCharacterList(destinyID):
    charURL = "https://stats.bungie.net/Platform/Destiny2/{}/Profile/{}/?components=100,200"
    platform = None
    for i in [3,2,1,4,5,10,254]:
        characterinfo = getJSONfromURL(charURL.format(i, destinyID))
        if characterinfo:
            return (i, list(characterinfo['Response']['characters']['data'].keys()))
    print(f'no account found for destinyID {destinyID}')
    return (None,None)
    

#https://bungie-net.github.io/multi/schema_Destiny-HistoricalStats-DestinyHistoricalStatsPeriodGroup.html#schema_Destiny-HistoricalStats-DestinyHistoricalStatsPeriodGroup
def getPlayersPastPVE(destinyID):
    platform = None
    syscharlist = getSystemAndChars(destinyID)
    if getLastUpdated(destinyID) < datetime.strptime("26/03/2015 04:20", "%d/%m/%Y %H:%M") or not syscharlist:
        platform, charIDs = getCharacterList(destinyID)
    else:
        (platform, _) = syscharlist[0]
        charIDs = [charid for (_,charid) in syscharlist]
    activitylist = []
    if not charIDs:
        return []

    for pagenr in range(1000):
        charidsToRemove = []
        for characterID in charIDs:
            staturl = f"https://www.bungie.net/Platform/Destiny2/{platform}/Account/{destinyID}/Character/{characterID}/Stats/Activities/?mode=7&count=250&page={pagenr}" 
            # None	0 Everything
            # Story	2	 
            # Strike	3	 
            # Raid	4	 
            # AllPvP	5	 
            # Patrol	6	 
            # AllPvE	7	
            rep = getJSONfromURL(staturl)
            if not rep or not rep['Response']:
                charidsToRemove.append(characterID)
                continue
            for activity in rep['Response']['activities']:
                yield activity
        for charid in charidsToRemove:
            charIDs.remove(charid)

    #return sorted(activitylist, key = lambda i: i['period'], reverse=True)

def getWeaponStats(destinyID):
    url = 'https://stats.bungie.net/Platform/Destiny2/{}/Account/{}/Stats/?groups=weapons'
    for system in [3,2,1,4,5,10,254]:
        statsResponse = getJSONfromURL(url.format(system, destinyID))
        if statsResponse:
            return statsResponse['Response']
    return None

def getNameToHashMapByClanid(clanid):
    requestURL = "https://www.bungie.net/Platform/GroupV2/{}/members/".format(clanid) #memberlist
    memberJSON = getJSONfromURL(requestURL)
    if not memberJSON:
        return {}
    memberlist = memberJSON['Response']['results']
    memberids  = dict()
    for member in memberlist:
        memberids[member['destinyUserInfo']['LastSeenDisplayName']] = member['destinyUserInfo']['membershipId']
    return memberids


def getPlatform(destinyID):
    charURL = "https://stats.bungie.net/Platform/Destiny2/{}/Profile/{}/?components=100,200"
    platform = None
    for i in [3,2,1,4,5,10,254]:
        characterinfo = getJSONfromURL(charURL.format(i, destinyID))
        if characterinfo:
            break
    return platform

def getPGCR(instanceID):
    pgcrurl = f'https://www.bungie.net/Platform/Destiny2/Stats/PostGameCarnageReport/{instanceID}/'
    return getJSONfromURL(pgcrurl)


def getManifest():
    manifest_url = 'http://www.bungie.net/Platform/Destiny2/Manifest/'
    binaryLocation = "cache/MANZIP"
    os.makedirs(os.path.dirname(binaryLocation), exist_ok=True)

    #get the manifest location from the json
    r = requests.get(manifest_url)
    manifest = r.json()
    mani_url = 'http://www.bungie.net' + manifest['Response']['mobileWorldContentPaths']['en']

    #Download the file, write it to 'MANZIP'
    r = requests.get(mani_url)
    with open(binaryLocation, "wb") as zip:
        zip.write(r.content)

    #Extract the file contents, and rename the extracted file to 'Manifest.content'
    with zipfile.ZipFile(binaryLocation) as zip:
        name = zip.namelist()
        zip.extractall()
    os.rename(name[0], 'cache/Manifest.content')

def fillDictFromDB(dictRef, table):
    if not os.path.exists('cache/' + table + '.json'): 
        if not os.path.exists('cache/Manifest.content'):
            getManifest()

        #Connect to DB
        con = sqlite3.connect('cache/Manifest.content')
        cur = con.cursor()

        #Query the DB
        cur.execute(
        '''SELECT 
            json
        FROM 
        ''' + table
        )
        items = cur.fetchall()
        item_jsons = [json.loads(item[0]) for item in items]
        con.close()

        #Iterate over DB-JSONs and put named ones into the corresponding dictionary
        for ijson in item_jsons:
            if 'name' in ijson['displayProperties'].keys():
                dictRef[ijson['hash']] = ijson['displayProperties']['name']
        with open('cache/' + table + '.json', 'w') as outfile:
            json.dump(dictRef, outfile)
    else:
        with open('cache/' + table + '.json') as json_file:
            dictRef.update(json.load(json_file))

fillDictFromDB(getNameFromHashRecords, 'DestinyRecordDefinition')
fillDictFromDB(getNameFromHashActivity, 'DestinyActivityDefinition')
fillDictFromDB(getNameFromHashCollectible, 'DestinyCollectibleDefinition')
fillDictFromDB(getNameFromHashInventoryItem, 'DestinyInventoryItemDefinition')

def insertIntoDB(destinyID, pve):
    period = datetime.strptime(pve['period'], "%Y-%m-%dT%H:%M:%SZ")
    activityHash = pve['activityDetails']['directorActivityHash']
    instanceID = pve['activityDetails']['instanceId']
    activityDurationSeconds = int(pve['values']['activityDurationSeconds']['basic']['value'])
    completed = int(pve['values']['completed']['basic']['value'])
    mode = int(pve['activityDetails']['mode'])
    if completed and not int(pve['values']['completionReason']['basic']['value']):
        pgcrdata = getPGCR(instanceID)['Response']
        startingPhaseIndex = pgcrdata['startingPhaseIndex']
        deaths = 0
        players = set()
        for player in pgcrdata['entries']:
            lightlevel = player['player']['lightLevel']
            playerID = player['player']['destinyUserInfo']['membershipId']
            players.add(playerID)
            characterID = player['characterId']
            playerdeaths = int(player['values']['deaths']['basic']['displayValue'])
            deaths += playerdeaths
            displayname = player['player']['destinyUserInfo']['displayName']
            completed = int(player['values']['completed']['basic']['value'])
            opponentsDefeated = player['values']['opponentsDefeated']['basic']['value']
            system = player['player']['destinyUserInfo']['membershipType']
            insertCharacter(playerID, characterID, system)
            insertInstanceDetails(instanceID, playerID, characterID, lightlevel, displayname, deaths, opponentsDefeated, completed)
        playercount = len(players)
        insertActivity(instanceID, activityHash, activityDurationSeconds, period, startingPhaseIndex, deaths, playercount, mode)
        
def updateDB(destinyID):
    with ThreadPoolExecutor(max_workers=10) as executor:
        processes = []
        lastUpdate = getLastUpdated(destinyID)
        updatedPlayer(destinyID)
        for pve in getPlayersPastPVE(destinyID):
            if 'period' not in pve.keys():
                print(pve)
            period = datetime.strptime(pve['period'], "%Y-%m-%dT%H:%M:%SZ")
            if period < lastUpdate + timedelta(days=1):
                print(f'stopped loading {destinyID} at ' + period.strftime("%d %m %Y"))
                updatedPlayer(destinyID)
                break
            processes.append(executor.submit(lambda args: insertIntoDB(*args), (destinyID, pve)))

        for task in as_completed(processes):
            if not task.result():
                return False


def initDB():
    con = db_connect()
    cur = con.cursor()
    playerlist = cur.execute('SELECT destinyID FROM discordGuardiansToken')
    playerlist = [p[0] for p in playerlist]
    for player in playerlist:
        updateDB(player)
        print(f'done updating {player}')

#TODO replace with DB and version checks
