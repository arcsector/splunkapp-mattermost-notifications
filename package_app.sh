#!/bin/bash

VERSION=$(grep version ./mattermost_alerts/default/app.conf | sed 's/version = //')
tar -czvf mattermost_alerts_$VERSION.tgz mattermost_alerts/