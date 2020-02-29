# ring-fhem
Python-based ring connector for FHEM.

Zur installation müssen zwei Python3.7 libs installiert werden:

    pip3.7 install git+https://github.com/tchellomello/python-ring-doorbell
    pip3.7 install fhem

Dann die zwei Dateien ring.py und run_ring runterladen und z.B. in /opt/fhem/bin ablegen.
In der ring.py muss noch der User und das Passwort des Ring Accounts eingetragen werden. Hier tuts auch ein Gast Account.

Die run_ring sorgt für die Ausführung der ring.py als user "fhem" und wird bei mir via crontab regelmäßig angetriggert (sollte mal ein Fehler unterlaufen):

    @reboot /opt/fhem/bin/run_ring
    @hourly /opt/fhem/bin/run_ring

Wenn noch kein token gespeichert wurde, wird beim Starten ein Benutzername/Passwort abgefragt, so wie der 2FA-Code welchen Ring an den Acount schickt. Nachdem dieser eingeben wurde wird ein AuthToken in einer Datei gesichertm so dass folgende Starts der ring.py ohne Interaktion funktionieren, in dem einfach das Token aus dem Cache gelesen und präsentiert wird.

In fhem habe ich einen Dummy angelegt mit dem Namen "Ring_[RingDeviceName]" (Achtung, wenn der Name nicht passt, muss die ring.py angepasst werden). [RingDeviceName] wird durch den Namen des Ring Devices ersetzt, wobei Leerzeichen entfernt werden. Bsp: Ring Device heißt "Front Door", in FHEM wird "Ring_FrontDoor" geschrieben. Der entsprechende Dummy wird wie folgt angelegt:

    define Ring_FrontDoor dummy
    attr Ring_FrontDoor setList none motion ring
    attr Ring_FrontDoor devStateIcon none:it_camera@green motion:secur_alarm@red ring:secur_alarm@orange

Ein DOIF sorgt dafür, dass der Status nach 5sec zurück gesetzt wird und eine Aktion ausgeführt wird. Beispiel wie folgt, FK_Haustuer ist ein Fenster/Türkontakt xmp3 eine Klingel:

    defmod Ring_FrontDoor_DOIF DOIF ([Ring_FrontDoor] eq "ring" and [FK_Haustuer] eq "closed" and [FK_Haustuer:state:sec] > 5)
    	(set xmp3 playTone 0) (set Ring_FrontDoor none)
    DOELSEIF ([Ring_FrontDoor] eq "motion" and [FK_Haustuer] eq "closed" and [FK_Haustuer:state:sec] > 2)
    	(set xmp3 playTone 48) (set Ring_FrontDoor none)
    DOELSE
    	(set Ring_FrontDoor none)  
    attr Ring_FrontDoor_DOIF cmdState ring,none|motion,none|none
    attr Ring_FrontDoor_DOIF do always
    attr Ring_FrontDoor_DOIF event-on-change-reading .*
    attr Ring_FrontDoor_DOIF stateFormat wait_timer
    attr Ring_FrontDoor_DOIF wait 0,5:0,5:0

Viel Erfolg!
