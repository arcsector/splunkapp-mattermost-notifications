#!/bin/bash

APP_DIR=mattermost_alert_action
if ! slim validate $APP_DIR; then
  echo "App Validation Failed" > /dev/stderr
  exit 1
fi
slim package $APP_DIR
