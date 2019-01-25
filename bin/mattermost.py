import sys
import json
import urllib2

from fnmatch import fnmatch


def send_notification(payload):
    settings = payload.get('configuration')
    print >> sys.stderr, "DEBUG Sending message with settings %s" % settings
    url = settings.get('url')
    print >> sys.stderr, "INFO Sending message to Mattermost url %s" % (url)
    msg = settings.get('message')
    msg_limit = 10000
    if len(msg) > msg_limit:
        print >> sys.stderr, "WARN Message is longer than limit of %d characters and will be truncated" % msg_limit
        msg = msg[0:msg_limit - 3] + '...'
    data = dict(
        text=msg,
        icon_url='https://www.splunk.com/content/dam/splunk2/images/icons/favicons/mstile-150x150.png',
        username='Splunk Alert',
    )

    body = json.dumps(data)
    print >> sys.stderr, 'DEBUG Calling url="%s" with body=%s' % (url, body)
    req = urllib2.Request(url, body, {"Content-Type": "application/json"})
    try:
        res = urllib2.urlopen(req)
        body = res.read()
        print >> sys.stderr, "INFO Mattermost server responded with HTTP status=%d" % res.code
        print >> sys.stderr, "DEBUG Mattermost server response: %s" % json.dumps(body)
        return 200 <= res.code < 300
    except urllib2.HTTPError, e:
        print >> sys.stderr, "ERROR Error sending message: %s (%s)" % (e, str(dir(e)))
        print >> sys.stderr, "ERROR Server response: %s" % e.read()
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        success = send_notification(payload)
        if not success:
            print >> sys.stderr, "FATAL Failed trying to send Mattermost notification"
            sys.exit(2)
        else:
            print >> sys.stderr, "INFO Mattermost notification successfully sent"
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
