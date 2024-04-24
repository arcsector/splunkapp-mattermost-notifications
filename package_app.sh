#!/bin/bash

APP_DIR=mattermost_alert_action
VERSION=$(grep version "./$APP_DIR/default/app.conf" | head -1 | sed 's/version = //' | sed 's/\n//')
tar -czvf "${APP_DIR}_${VERSION//./}.tgz" "$APP_DIR/"
