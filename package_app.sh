#!/bin/bash

logphrase() {
    BLUE='\033[0;34m' 
    NC='\033[0m'
    echo -e "${BLUE}$APP_DIR${NC}: $1"
}

CURRENT_DIR=$(pwd)
APP_DIR=mattermost_alert_action
BUILD_DIR="$HOME/.splunk-build"
if ! slim validate $APP_DIR; then
    echo "$APP_DIR Package: App Validation Failed" > /dev/stderr
    exit 1
fi
if [ ! -d "$BUILD_DIR" ]; then
    logphrase "Creating Build Directory at '$BUILD_DIR'"
    mkdir "$BUILD_DIR"
else
    logphrase "Cleaning build directory at '$BUILD_DIR'"
    rm -rf "${BUILD_DIR:?}/*"
fi
if test -d "$BUILD_DIR/$APP_DIR"; then
    logphrase "Removing existing content in Build Directory"
    rm -rf "${BUILD_DIR:?}/$APP_DIR"
fi
cp -r $APP_DIR "$BUILD_DIR/"
cd "$BUILD_DIR" || exit 1
logphrase "Changing permissions to 660 for non-bin dirs"
#chmod -R u=rwX,go= "$APP_DIR"
find "$APP_DIR" -type f -exec chmod u=rw,go= {} + 
find "$APP_DIR" -type d -exec chmod u=rwX,go= {} +
chmod -R u+x "$APP_DIR/bin/"
splunk-appinspect inspect $APP_DIR/ --generate-feedback --excluded-tags manual --ci --output-file results.json > /dev/null
AppInspectResult=$?
if test $AppInspectResult -eq 101; then
    echo "$APP_DIR Package: AppInspect Failed with code '$AppInspectResult' - check results.json and inspect.yml" > /dev/stderr
    cp inspect.yml results.json "$CURRENT_DIR"
    exit 1
fi
logphrase "No AppInspect Failures"
if test "$1" == "debug"; then
    exit 0
fi
slim package $APP_DIR -o "$CURRENT_DIR"
