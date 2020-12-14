# /usr/bin/python3
# 
# David DURVAUX - david@autopsit.org
# version 2020-06-08
#
import json
import urllib
import pickle
import requests
import argparse
import http.cookiejar
from datetime import datetime
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import paho.mqtt.publish as publish    # apt-get install python3-paho-mqtt

# -----------------------------------------------------------------------------

# Authentication settings
# Change here
AuthCard = { "A1" : "0000",  "B1" : "0000",  "C1" : "0000",  "D1" : "0000",  "E1" : "0000",  "F1" : "0000", 
             "A2" : "0000",  "B2" : "0000",  "C2" : "0000",  "D2" : "0000",  "E2" : "0000",  "F2" : "0000", 
             "A3" : "0000",  "B3" : "0000",  "C3" : "0000",  "D3" : "0000",  "E3" : "0000",  "F3" : "0000", 
             "A4" : "0000",  "B4" : "0000",  "C4" : "0000",  "D4" : "0000",  "E4" : "0000",  "F4" : "0000", 
             "A5" : "0000",  "B5" : "0000",  "C5" : "0000",  "D5" : "0000",  "E5" : "0000",  "F5" : "0000"  }
PinCode = 1234
AlarmURL = "http://192.168.0.1"
User = "u" # Utilisateur1 = u; Installateur = i; Télésurveillance = t
debug = False

# Trigger IFFT Event
webhook_url = "https://maker.ifttt.com/trigger/%s/with/key/%s"
webhook_key = "azertyuiop"
webhook_arm = "alarm_armed"
webhook_disarm = "alarm_disarmed"

# MQTT info
IDZONEA = 1
IDZONEB = 2
IDZONEC = 3
IDCAMERA = 4
MQTTSRV = "127.0.0.1"

# Keeping status
status = {
    "alarm_armed" : False,
    "last_check" : ""
}

# -----------------------------------------------------------------------------
def __get2FA():
    """
        Parse login page to retrieve the 2nd factor
    """
    try:
        query = "%s/fr/login.htm" % AlarmURL
        if debug:
            print("QUERYING: %s" % query)

        html = urllib.request.urlopen(query)
        soup = BeautifulSoup(html, 'html5lib')
        form_table = soup.form.table.tbody
        for line in form_table.findAll("tr"):
            for td in line.findAll("td"):
                if "Code d'authentification" in td.prettify():
                    code = td.b.string
                    if debug:
                        print("CODE: %s => %s" % (code, AuthCard[code]))
                    return code
    except urllib.error.HTTPError as e:
        print(e)
    except urllib.error.URLError as e:
        print("The server could not be found!")
    except Exception as e:
        print(str(e))
    return None


# Login Table:
#   login -> User
#   password -> PinCode
#   key -> AuthCard[Code d'authentification]
def authenticate(user, pin, sec_fa):
    """
        Authenticate on the alarm login page
        POST login=u&password=1234&key=1234&btn_login=Connexion

        Note: while authenticated, the alarm don't care about cookie or session ID :)
              seems that it just look at source IP...
    """
    try:
        query = "%s/fr/login.htm" % AlarmURL
        data = urllib.parse.urlencode({"login" : user, "password" : pin, "key" : sec_fa, "btn_login" : "Connexion"}).encode()
        #cj = http.cookiejar.CookieJar()
        #opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        request =  urllib.request.Request(query, data=data) # this will make the method "POST"
        response = urllib.request.urlopen(request)
        if debug:
            print(response.read())
        return True
    except urllib.error.HTTPError as e:
        print(e)
    except urllib.error.URLError as e:
        print("The server could not be found!")
    except Exception as e:
        print(str(e))
    return None


def getStatus():
    """
    Parse the status.xml page

        <?xml version="1.0" encoding="iso-8859-15"?>
        <response>
            <zone0>off</zone0>
            <zone1>on</zone1>
            <zone2>off</zone2>
            <defaut0>ok</defaut0>
            <defaut1>ok</defaut1
            <defaut2>ok</defaut2>
            <defaut3>ok</defaut3>
            <defaut4>ok</defaut4>
            <gsm>GSM connect\xc3\xa9 au r\xc3\xa9seau</gsm>
            <recgsm>5</recgsm>
            <opegsm>"BASE"</opegsm>
            <camera>disabled</camera>
        </response>
    """
    try:
        status = {}
        query = "%s/status.xml" % AlarmURL
        response = urllib.request.urlopen(query)
        root = ET.fromstring(response.read())
        for child in root:
            status[child.tag] = child.text
            if debug:
                print("%s : %s" % (child.tag, child.text))
        return status
    except urllib.error.HTTPError as e:
        print(e)
    except urllib.error.URLError as e:
        print("The server could not be found!")
    except Exception as e:
        print(str(e))
    return None
    

def isAlarmArmed(status):
    """
        {'zone0': 'off', 
         'zone1': 'off', 
         'zone2': 'off',
         [...]}
    """
    # push status via MQTT
    if(status["zone0"] == "off"):
        publish.single("domoticz/in", json.dumps({"command": "switchlight", "idx": IDZONEA, "switchcmd": "Off"}), hostname=MQTTSRV)
    else:
        publish.single("domoticz/in", json.dumps({"command": "switchlight", "idx": IDZONEA, "switchcmd": "On"}), hostname=MQTTSRV)
    if(status["zone1"] == "off"):
        publish.single("domoticz/in", json.dumps({"command": "switchlight", "idx": IDZONEB, "switchcmd": "Off"}), hostname=MQTTSRV)
    else:
        publish.single("domoticz/in", json.dumps({"command": "switchlight", "idx": IDZONEB, "switchcmd": "On"}), hostname=MQTTSRV)
    if(status["zone2"] == "off"):
        publish.single("domoticz/in", json.dumps({"command": "switchlight", "idx": IDZONEC, "switchcmd": "Off"}), hostname=MQTTSRV)
    else:
        publish.single("domoticz/in", json.dumps({"command": "switchlight", "idx": IDZONEC, "switchcmd": "On"}), hostname=MQTTSRV)


    # check Alarm status
    if(status["zone0"] == "off" and status["zone1"] == "off" and status["zone2"] == "off"):
        status["alarm_armed"] = False
        if(debug):
            print("Alarme is disarmed")
        return False
    else:
        status["alarm_armed"] = True
        if(debug):
            print("Alarme is armed")
        return True


def disableArlo():
    if(debug):
        print("Disarm Arlo")
    publish.single("domoticz/in", json.dumps({"command": "switchlight", "idx": IDCAMERA, "switchcmd": "Off"}), hostname=MQTTSRV)
    url = webhook_url % (webhook_disarm, webhook_key)
    r = requests.post(url)
    if(debug):
        print(r)
    return


def enableArlo():
    if(debug):
        print("Arm Arlo")
    publish.single("domoticz/in", json.dumps({"command": "switchlight", "idx": IDCAMERA, "switchcmd": "On"}), hostname=MQTTSRV)
    url = webhook_url % (webhook_arm, webhook_key)
    r = requests.post(url)
    if(debug):
        print(r)
    return


def loadStatus(filename="/tmp/status.json"):
    try:
        with open(filename, "rb") as pickle_file:
            global status
            status = pickle.load(pickle_file)
            if(debug):
                print("Loading: %" % status)
            return status
    except Exception as e:
        print("Impossible to load status to %s (%s)" % (filename, e))
    return None


def saveStatus(filename="/tmp/status.json"):
    global status
    now = datetime.now()
    status["last_check"] = now.strftime("%Y-%m-%d %H:%M:%S")
    if(debug):
        print("Saving: %s" % status)
    try:
        with open(filename, 'wb') as pickle_file:
            pickle.dump(status, pickle_file)
    except Exception as e:
        print("Impossible to save status to %s (%s)" % (filename, e))
    return


def signArloWithAlarm():
    """
    Turn camera ON if alarm is set and OFF if alarme is disabled
    """
    # Authenticate
    logged = True # Suppose it's always logged on - should be improved
    sec_fa  = __get2FA()
    if sec_fa is not None:
        logged = authenticate(User, PinCode, AuthCard[sec_fa])
    if logged:
        global status
        loadStatus()
        curstate = getStatus()
        if(isAlarmArmed(curstate) and not(status["alarm_armed"])):
            print("Enable Arlo monitoring")
            status["alarm_armed"] = True
            enableArlo()
        elif(status["alarm_armed"] and not(isAlarmArmed(curstate))):
            print("Disable Arlo monitoring")
            status["alarm_armed"] = False
            disableArlo()
        else:
            print("No change, keeping Arlo as it was")
    saveStatus()
    print("Alarm checked at %s and status is %s" % (status["last_check"], status["alarm_armed"]))


def main():
    """
        Main function, to be called when used as CLI tool
    """
    # Argument definition
    parser = argparse.ArgumentParser(description='Integration of Arlo Camera with Somfy Protexiom')
    parser.add_argument('-e', '--enable-arlo', action='store_true', dest='enable', help='Enable Arlo Camera')
    parser.add_argument('-d', '--disable-arlo', action='store_true', dest='disable', help='Disable Arlo Camera')
    parser.add_argument('-s', '--sync-arlo', action='store_true', dest='sync', help='Sync Arlo Camera with Protexiom status')
    args = parser.parse_args()

    if(args.enable):
        enableArlo()
    elif(args.disable):
        disableArlo()
    else:
        signArloWithAlarm()
    return
    


# --------------------------------------------------------------------------- #

"""
   Call main function
"""
if __name__ == "__main__":

    # Create an instance of the Analysis class (called "base") and run main
    main()


# -----------------------------------------------------------------------------
# That's all folk ;)
