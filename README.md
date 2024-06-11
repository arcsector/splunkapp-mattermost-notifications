# Mattermost Alert Action app for Splunk

This app is built on top of the app forked from Florian Coulmier, and updated to be compliant with:

- Splunk Cloud
- Python 3
- Splunk v9.X
- AppInspect

The repo contains the following features:

1. App repository with new `app.manifest` for Splunk Cloud, alert_actions.conf.spec for passing validation, and new `app.conf` properties
2. `test_payloads` directory for testing your own mattermost server's compatibility with this app
3. `.pylintrc` file for linting `mattermost.py` file
4. `package_app.sh` script for validating and packaging app in one command on WSL2
5. `test_mm.sh` script for testing all the `test_payloads` JSON payloads
