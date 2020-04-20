**Changelog**

# v 1.0 - added: threadded video download

If a motion or ding event occurs, the handling for downloading the video gets handled in a separate thread. This enables the script to handle subsequent events like a ding event after a motion event.

# v 1.0.1 - added local vars to threadded function
Moved some vars into the local context of the threadded function to isolate the events' information

# v 1.0.2 - added utf-8 encoding for handling umlauts
Switched the default encoding to utf8 for the running python script. This allows for proper utf-8-encoding and -decoding, when trying to send attribute updates to FHEM

# v 1.0.3 - switched to Python3
Switched to Python3, due to changes in tchellomello/python-ring-doorbell
library. E.g. the OAuth2 lib seems to be Python3-only

# v 1.0.4 - integrated new Auth function
On startup, ring.py will login and request a new auth token using user/pass for the ring site

# v 1.0.5 - fixed threading for Python3
Correct the threading call for gathering the videos from the ring site

# v 1.0.6 - compatibiliy adjustements for pyhthon-ring-doorbell lib - current master branch.
Needs Python3.7
Added 2FA authentication
Added interactive user/passwords
Reworked code for compatibility with tchellomello/python-ring-doorbell master(0.6.0+)
Fixed getting lastCaptureURL from Ring api

# v 1.0.7 - added authorized_doorbots to list of monitored devices
Doorbots which have been granted to "neighbour" users are now gathered from
the Ring api

# v 1.0.8 - downloading videos Reworked
Instead of calling the history repeatedly and determine, if the new video is videoIsReadyForDownload
we leave that to the new recording_download function of the library

# v 1.0.9 - added exception handling for ring api connectionStatus
If the connection to the ring api fails, retry up to 600s before giving up and terminating

# v 1.0.11 - fixed video download
added backgound readings update

# v 1.0.12 - added snapshot download each time a backgound readings updates
# is performed
added backgound readings update
