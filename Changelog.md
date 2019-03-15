**Changelog**

# v 1.0 - added: threadded video download

If a motion or ding event occurs, the handling for downloading the video gets handled in a separate thread. This enables the script to handle subsequent events like a ding event after a motion event.

# v 1.0.1 - added local vars to threadded function
Moved some vars into the local context of the threadded function to isolate the events' information

# v 1.0.2 - added utf-8 encoding for handling umlauts
Switched the default encoding to utf8 for the running python script. This allows for proper utf-encoding and decoding, when trying to send atrribute updates to FHEM
