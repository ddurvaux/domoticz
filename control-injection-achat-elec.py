import os
import json
from datetime import datetime
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish    # apt-get install python3-paho-mqtt

#
# Control injection / purchase of electricity based on 
# - current consumption
# - current production
#
# Version: 2022-10-08
# Copyright: David DURVAUX (david@autopsit.org)

# MQTT info
PRODID1 = 601 # String1 - SMA Sunny Boy 
PRODID2 = 602 # String2 - SMA Sunny Boy
CONSOM  = 521 # Consumption
INJECT  = 645 # Injection
PURCHASE = 647 # Purchase
MQTTSRV = "127.0.0.1"

# Logging Info
LogPath = "/home/david/production/proddata.csv"   # where to save data (in CSV format)

# Current status
logcsv = None
string1 = -1 # set to 0 by default
string2 = -1
total = -1
purchase = 0.0
inject = 0.0
totalp = 0.0 # total purchase
totali = 0.0 # total inject


def on_inject(inject):
    return

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("domoticz/out/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global string1
    global string2
    global total
    global purchase
    global inject
    global totalp
    global totali
    global logcsv

    # recover message content
    content = json.loads(msg.payload)

    # only capture messages related to solar pannels
    # Typical output:
    # { 'Battery': 255, 
    #   'LastUpdate': '2022-09-12 21:33:02', 
    #   'RSSI': 12, 
    #   'description': '', 
    #   'dtype': 'Usage', 
    #   'hwid': '11', 
    #   'id': '000B0003', 
    #   'idx': 602, 'name': 'SunnyBoy - DC Power B', 
    #   'nvalue': 0, 
    #   'stype': 'Electric', 
    #   'svalue1': '0', 
    #   'unit': 3 }
    id = content["idx"]

    # Compute current production
    if(id in [PRODID1, PRODID2]):
        val  = float(content["svalue1"])
        if(id == PRODID1):
            string1 = val
        else:
            string2 = val

        # compute current production and send result 
        if(string1 >= 0 and string2 >= 0):
            total = string1 + string2
            string1 = -1
            string2 = -1

    # Get current consumption
    if(id == CONSOM):
        val  = float(content["svalue1"])
        if(total >= 0):
            inject = total - val
            purchase = val - total
           
            # Log status to CSV
            # Format: 'DateTime;Production;Injection;Consumption'
            line  = '%s;%d;%d;%d'   % (datetime.now().isoformat(), total, inject, purchase)
            print(line + '\n')

            try:
                logcsv.write(line + '\n')
            except:
                pass

            # Format
            # {'Battery': 255, 'LastUpdate': '2022-10-08 11:50:24', 
            #  'RSSI': 12, 'description': '', 
            #  'dtype': 'Usage', 'hwid': '11', 'id': '000B0002', 'idx': 601, 
            #  'name': 'SunnyBoy - DC Power A', 
            #  'nvalue': 0, 
            #  'stype': 'Electric', 'svalue1': '655', 'unit': 2}
            # We are purchasing electricity --> update status
            if(purchase >= 0):
                totalp = totalp + purchase
                publish.single("domoticz/in", json.dumps({"stype": "Electric", "idx": PURCHASE, "svalue": str(purchase)}), hostname=MQTTSRV)
                purchase = 0.0
            else:
                publish.single("domoticz/in", json.dumps({"stype": "Electric", "idx": PURCHASE, "svalue": str(0)}), hostname=MQTTSRV)
            # We are injecting electricity --> update status
            if(inject >= 0):
                totali = totali + inject
                on_inject(totali)
                publish.single("domoticz/in", json.dumps({"stype": "Electric", "idx": INJECT, "svalue": str(inject)}), hostname=MQTTSRV)
                inject = 0.0
            else:
                publish.single("domoticz/in", json.dumps({"stype": "Electric", "idx": INJECT, "svalue": str(0)}), hostname=MQTTSRV) 
               
    return


def main():
    """
        Main function, to be called when used as CLI tool
    """
    # Initiate listener
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTTSRV, 1883, 60)

    # Initiate Logging
    global logcsv
    proddata = LogPath
    headline = 'DateTime;Production;Injection;Consumption'
    logcsv = open(proddata, "a")  
    logcsv.write(headline + '\n')

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()
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
