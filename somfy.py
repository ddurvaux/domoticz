# /usr/bin/python3
# 
# David DURVAUX - david@autopsit.org
# version 2020-06-08
#
import urllib
import pickle
import requests
import http.cookiejar
from datetime import datetime
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET


# -----------------------------------------------------------------------------

# Authentication settings
# Change here
AuthCard = { "A1" : "0000",  "B1" : "8888",  "C1" : "1212",  "D1" : "4321",  "E1" : "1234",  "F1" : "0000", 
             "A2" : "0000",  "B2" : "8888",  "C2" : "1212",  "D2" : "4321",  "E2" : "1234",  "F2" : "0000", 
             "A3" : "0000",  "B3" : "8888",  "C3" : "1212",  "D3" : "4321",  "E3" : "1234",  "F3" : "0000", 
             "A4" : "0000",  "B4" : "8888",  "C4" : "1212",  "D4" : "4321",  "E4" : "1234",  "F4" : "0000", 
             "A5" : "0000",  "B5" : "8888",  "C5" : "1212",  "D5" : "4321",  "E5" : "1234",  "F5" : "0000"  }
PinCode = 0000
AlarmURL = "http://192.0.0.1"
User = "u" # Utilisateur1 = u; Installateur = i; Télésurveillance = t
debug = False

# Trigger IFFT Event
# curl -X POST https://maker.ifttt.com/trigger/alarm_disarmed/with/key/<key>
# curl -X POST https://maker.ifttt.com/trigger/alarm_armed/with/key/<key>
webhook_url = "https://maker.ifttt.com/trigger/%s/with/key/%s"
webhook_key = "foobar"
webhook_arm = "alarm_armed"
webhook_disarm = "alarm_disarmed"

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
        # http://192.168.100.227/fr/login.htm
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
    url = webhook_url % (webhook_disarm, webhook_key)
    r = requests.post(url)
    if(debug):
        print(r)
    return


def enableArlo():
    if(debug):
        print("Arm Arlo")
    url = webhook_url % (webhook_arm, webhook_key)
    r = requests.post(url)
    if(debug):
        print(r)
    return


def loadStatus(filename="/tmp/status.json"):
    try:
        with open(filename, "rb") as pickle_file:
            status = pickle.load(pickle_file)
            return status
    except Exception as e:
        print("Impossible to load status to %s (%s)" % (filename, e))
    return None


def saveStatus(filename="/tmp/status.json"):
    now = datetime.now()
    status["last_check"] = now.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(filename, 'wb') as pickle_file:
            pickle.dump(status, pickle_file)
    except Exception as e:
        print("Impossible to save status to %s (%s)" % (filename, e))
    return


def main():
    """
        Main function, to be called when used as CLI tool
    """
    # Authenticate
    logged = True # Suppose it's always logged on - should be improved
    sec_fa  = __get2FA()
    if sec_fa is not None:
        logged = authenticate(User, PinCode, AuthCard[sec_fa])
    if logged:
        loadStatus()
        curstate = getStatus()
        if(isAlarmArmed(curstate) and not status["alarm_armed"]):
            print("Enable Arlo monitoring")
            enableArlo()
        elif(status["alarm_armed"]):
            print("Disable Arlo monitoring")
            disableArlo()
        else:
            print("No change, keeping Arlo as it was")
    saveStatus()
    print("Alarm checked at %s and status is %s" % (status["last_check"], status["alarm_armed"]))


# --------------------------------------------------------------------------- #

"""
   Call main function
"""
if __name__ == "__main__":

    # Create an instance of the Analysis class (called "base") and run main
    main()


# -----------------------------------------------------------------------------
# That's all folk ;)