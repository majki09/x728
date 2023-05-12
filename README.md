## This is actually forked from https://github.com/geekworm-com/x728 with some nice mods.

User guide: https://wiki.geekworm.com/X728-Software

# Main loop diagram

![diagram](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/majki09/x728/master/diagram_main_loop.puml)

# Installation
## As systemd service
Copy *x728.service* file to services folder and optionally change the *x728* script path.

```
cp x728.service /lib/systemd/system/
sudo chmod 644 /lib/systemd/system/x728.service
chmod +x x728v2-asd.py
sudo systemctl daemon-reaload
sudo systemctl enable x728.service
sudo systemctl start x728.service
```

From now on the *x728v2-asd.py* should start automatically with system boot and run in the background.

Logs can be found with

` journalctl -u x728.service `

## As auto-run entry in *rc.local*
Add this line to */etc/rc.local/*

` python3 /home/pi/x728/x728v2-asd.py & `

From now on the *x728v2-asd.py* should start automatically with system boot and run in the background.

If you want to find the logs consider *systemd service* way.

