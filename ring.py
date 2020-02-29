# A little Python3 app, which queries Ring products and integrates
# them with Fhem
#
# v 1.0.6

import json
import time
import fhem
import getpass
from pathlib import Path
import logging
import threading
import _thread
import sys  # import sys package, if not already imported
from ring_doorbell import Ring, Auth
from oauthlib.oauth2 import MissingTokenError
from _thread import start_new_thread, allocate_lock

cache_file = Path("ring_token.cache")



# CONFIG
ring_user = 'user@foo.bar'
ring_pass = 'password'
fhem_ip   = '127.0.0.1'
fhem_port = 7072 # Telnet Port
log_level = logging.DEBUG
fhem_path = '/opt/fhem/www/ring/' # for video downloads
POLLS     = 2 # Poll every x seconds

# thread-related VARs
# checkForVideoRunning = False # safeguard against race-condition

# LOGGING
logger = logging.getLogger('ring_doorbell.doorbot')
logger.setLevel(log_level)

# create file handler which logs even debug messages
fh = logging.FileHandler('ring.log')
fh.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

logger = logging.getLogger('fhem_ring')
logger.setLevel(log_level)
logger.addHandler(ch)
logger.addHandler(fh)


# Connecting to RING.com
def token_updated(token):
    cache_file.write_text(json.dumps(token))

def otp_callback():
    auth_code = input("2FA code: ")
    return auth_code

if cache_file.is_file():
    auth = Auth("MyProject/1.0", json.loads(cache_file.read_text()), token_updated)
else:
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    auth = Auth("MyProject/1.0", None, token_updated)
    try:
        auth.fetch_token(username, password)
    except MissingTokenError:
        auth.fetch_token(username, password, otp_callback())

myring = Ring(auth)
myring.update_data()


fh = fhem.Fhem(fhem_ip, fhem_port)

def sendFhem(str):
    logger.debug("sending: " + str)
    global fh
    fh.send_cmd(str)

def askFhemForReading(dev, reading):
    logger.debug("ask fhem for reading " + reading + " from device " + dev)
    return fh.get_dev_reading(dev, reading)

def askFhemForAttr(dev, attr, default):
    logger.debug("ask fhem for attribute "+attr+" from device "+dev+" (default: "+default+")")
    fh.send_cmd('{AttrVal("'+dev+'","'+attr+'","'+default+'")}')
    data = fh.sock.recv(32000)
    return data

def setRing(str, dev):
    sendFhem('set Ring_' + dev.name.replace(" ","") + ' ' + str)

def attrRing(str, dev):
    sendFhem('attr Ring_' + dev.name.replace(" ","") + ' ' + str)

def srRing(str, dev):
    sendFhem('setreading Ring_' + dev.name.replace(" ","") + ' ' + str)

num_threads = 0
thread_started = False
lock = allocate_lock()

def getDeviceInfo(dev):
    # dev.update()
    logger.info("Updating device data for device '"+dev.name+"' in FHEM...")
    # from generc.py
    srRing('name ' + str(dev.name), dev)
    srRing('id ' + str(dev.device_id), dev)
    srRing('family ' + str(dev.family), dev)
    srRing('model ' + str(dev.model), dev)
    srRing('address ' + str(dev.address), dev)
    srRing('firmware ' +str(dev.firmware), dev)
    srRing('latitude ' + str(dev.latitude), dev)
    srRing('longitude ' + str(dev.longitude), dev)
    srRing('kind ' + str(dev.kind), dev)
    srRing('timezone ' + str(dev.timezone), dev)
    srRing('WifiName ' + str(dev.wifi_name), dev)
    srRing('WifiRSSI ' + str(dev.wifi_signal_strength), dev)
    srRing('WifiCategory ' + str(dev.wifi_signal_category), dev)
    # from doorbot.py
    srRing('Model ' + str(dev.model), dev)
    srRing('battery ' + str(dev.battery_life), dev)
    srRing('doorbellType ' + str(dev.existing_doorbell_type), dev)
    srRing('subscribed ' + str(dev.subscribed), dev)
    srRing('ringVolume ' + str(dev.volume), dev)
    srRing('connectionStatus ' + str(dev.connection_status), dev)


def pollDevices():
    logger.info("Polling for events.")
    global tmp

    i=0
    while 1:
        for poll_device in tmp:
            myring.update_dings()
            logger.debug("Polling for events with '" + poll_device.name + "'.")
            logger.debug("Connection status '" + poll_device.connection_status + "'.")
            # logger.debug("Last URL: " + poll_device.recording_url(poll_device.last_recording_id))

            if myring.dings_data:
                dingsEvent = myring.dings_data[0]
                logger.debug("Dings: " + str(myring.dings_data))
                logger.debug("State: " + str(dingsEvent["state"]))
                logger.info("Alert detected at '" + poll_device.name + "'.")
                logger.debug("Alert detected at '" + poll_device.address + "' via '" + poll_device.name + "'.")
                alertDevice(poll_device,dingsEvent,str(dingsEvent["state"]))
            time.sleep(POLLS)
        i+=1
        if i>600:
            break

def findHistoryItem(historyArry,id):
    ret = None
    for singleItem in historyArry:
        if (singleItem['id']==id):
            ret = singleItem
            break
    return ret

def waitForVideoDownload(alertID,alertKind,ringDev):
    # global checkForVideoRunning
    videoIsReadyForDownload = None
    counti = 1
    while (videoIsReadyForDownload is None):
        logger.debug(str(counti) + ". Try to find hitory and video in history data list")
        logger.debug("  historyID:"+str(alertID))
        try:
            singleHistoryItem = findHistoryItem(ringDev.history(limit=10,kind=alertKind),alertID)
            if singleHistoryItem and singleHistoryItem['id'] == alertID :
                logger.debug("History item found!")
                if singleHistoryItem['recording']['status'] == 'ready':
                    logger.debug("Video is now ready to downloading")
                    videoIsReadyForDownload = True
        except Exception as inst:
            logger.debug("Repeating...")
        time.sleep(1)
        counti+=1
        if (counti>240):
            logger.debug("Stop trying to find history and video data")
            break

    if (alertKind == 'ding') and videoIsReadyForDownload:
        logger.debug("Start downloading new ding video now")
        ringDev.recording_download(alertID, filename=fhem_path + 'last_ding_video.mp4',override=True)
        srRing('lastDingVideo ' + fhem_path + 'last_ding_video.mp4', ringDev)

    elif (alertKind == 'motion') and videoIsReadyForDownload:
        logger.debug("Start downloading new motion video now")
        ringDev.recording_download(alertID, filename=fhem_path + 'last_motion_video.mp4',override=True)
        srRing('lastMotionVideo ' + fhem_path + 'last_motion_video.mp4', ringDev)

    if videoIsReadyForDownload:
        srRing('lastCaptureURL ' + str(ringDev.recording_url(ringDev.last_recording_id)), ringDev)
    #checkForVideoRunning = False

def downloadLatestDingVideo(doorbell,dingsEvent,lastAlertKind):
    logger.debug("Trying to download latest Ding-Video")
    doorbell.recording_download(
        doorbell.history(limit=100, kind=str(lastAlertKind))[0]['id'],
                        filename='last_ding.mp4',
                        override=True)
    srRing('lastDingVideo ' + fhem_path + 'last_'+str(lastAlertKind)+'_video.mp4', poll_device)

def getLastCaptureVideoURL(doorbell):
    lastCaptureURL = doorbell.recording_url(doorbell.last_recording_id)
    srRing('lastCaptureURL ' + str(lastCaptureURL), doorbell)

def alertDevice(poll_device,dingsEvent,alert):
    # global checkForVideoRunning
    lastAlertID = str(dingsEvent["id"])
    lastAlertKind = str(dingsEvent["kind"])
    logger.debug("lastAlertID:"+str(lastAlertID))
    logger.debug("lastAlertKind:"+str(lastAlertKind))

    srRing('lastAlertDeviceID ' + str(poll_device.device_id), poll_device)
    srRing('lastAlertDeviceName ' + str(poll_device.name), poll_device)
    srRing('lastAlertSipTo ' + str(dingsEvent["sip_to"]), poll_device)
    srRing('lastAlertSipToken ' + str(dingsEvent["sip_token"]), poll_device)


    if (lastAlertKind == 'ding'):
        logger.debug("Signalling ring to FHEM")
        setRing('ring', poll_device)
        srRing('lastAlertType ring', poll_device)
    elif (lastAlertKind == 'motion'):
        logger.debug("Signalling motion to FHEM")
        srRing('lastAlertType motion', poll_device)
        setRing('motion', poll_device)
    #if ((lastAlertKind == 'ding' or lastAlertKind == 'motion') and not checkForVideoRunning):
    #    checkForVideoRunning = True
    if poll_device.recording_url(poll_device.last_recording_id):
        _thread.start_new_thread(getLastCaptureVideoURL,(poll_device,))
        # _thread.start_new_thread(downloadLatestDingVideo,(poll_device,dingsEvent,lastAlertKind))
        # _thread.start_new_thread(waitForVideoDownload,(lastAlertID,lastAlertKind,poll_device))



# GATHERING DEVICES
devs = myring.devices()
poll_device = None
tmp = list(devs['doorbots'])
logger.debug(tmp)
for t in tmp:
    t.update_health_data()
    logger.debug(t.address)
    # devs[t.id] = t
    # all alerts can be recognized on all devices
    poll_device = t # take one device for polling

logger.info("Found " + str(len(tmp)) + " devices.")
getDeviceInfo(t)

# START POLLING DEVICES
count = 1
while count<6:  # try 5 times
    try:
        while 1:
            # for k, d in devs(): getDeviceInfo(d)
            pollDevices()

    except Exception as inst:
        logger.error("Unexpected error:" + str(inst))
        logger.error("Exception occured. Retrying...")
        time.sleep(5)
        if count == 5:
            raise

        count += 1
