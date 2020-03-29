# /usr/bin/python3
# 
# David DURVAUX - david@autopsit.org
# version 2020-03-29
#
import urllib
import http.cookiejar
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# -----------------------------------------------------------------------------

# Authentication settings
# Change here
AuthCard = { "A1" : "1234",  "B1" : "1234",  "C1" : "1234",  "D1" : "1234",  "E1" : "1234",  "F1" : "1234", 
             "A2" : "1234",  "B2" : "1234",  "C2" : "1234",  "D2" : "1234",  "E2" : "1234",  "F2" : "1234", 
             "A3" : "1234",  "B3" : "1234",  "C3" : "1234",  "D3" : "1234",  "E3" : "1234",  "F3" : "1234", 
             "A4" : "1234",  "B4" : "1234",  "C4" : "1234",  "D4" : "1234",  "E4" : "1234",  "F4" : "1234", 
             "A5" : "1234",  "B5" : "1234",  "C5" : "1234",  "D5" : "1234",  "E5" : "1234",  "F5" : "1234"  }
PinCode = 1234
AlarmURL = "http://192.168.0.2"
User = "u" # Utilisateur1 = u; Installateur = i; Télésurveillance = t
debug = True

# -----------------------------------------------------------------------------
def __get2FA():
    """
        Parse login page to retrieve the 2nd factor
    """
    try:
        # http://192.168.0.2/fr/login.htm
        query = "%s/fr/login.htm" % AlarmURL
        if debug:
            print("QUERYING: %s" % query)

        html = urllib.request.urlopen(query)
        soup = BeautifulSoup(html)
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
            <opegsm>"ORANGE"</opegsm>
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
        status = getStatus()
        print(status)


# --------------------------------------------------------------------------- #

"""
   Call main function
"""
if __name__ == "__main__":

    # Create an instance of the Analysis class (called "base") and run main
    main()


# -----------------------------------------------------------------------------
# That's all folk ;)
