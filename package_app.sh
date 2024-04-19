#!/bin/bash

VERSION=$(grep version ./mattermost_alerts/default/app.conf | head -1 | sed 's/version = //' | sed 's/\n//')
tar -czvf "mattermost_alerts_$VERSION.tgz" mattermost_alerts/