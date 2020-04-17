import sys
import json
import urllib2
import gzip
import csv

from fnmatch import fnmatch

def create_markdown_string(value_list):
    return '|' + '|'.join(value_list) + '|\n'

def create_markdown_separator(value_list):
    markdown_string = "|"
    for value in value_list:
        markdown_string = '-|'
    print >> sys.stderr "DEBUG Markdown header length is %s" %s str(value_list)
    return markdown_string

def send_notification(msg, url):
    print >> sys.stderr, "INFO Sending message to Mattermost url %s" % (url)
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

def table_broker(payload):
    settings = payload.get('configuration')
    print >> sys.stderr, "DEBUG Sending message with settings %s" % settings
    table = settings.get('table')
    msg = settings.get('message')
    url = settings.get('url')
    return_value = send_notification(msg, url)
    if table:
        results_file_location = settings.get('results_file')
        print >> sys.stderr, "INFO Results table at %s" % results_file_location
        with gzip.open(results_file_location, 'rb') as results_file:
            results = csv.reader(results_file)
            header_line = next(results)
            data = list(results)
            results_string = create_markdown_string(header_line)
            results_string = results_string + create_markdown_separator(header_line)
            results_string = [create_markdown_string(line) for line in data]
            table_return_value = send_notification(results_string, url)
            if not success:
                print >> sys.stderr, "FATAL Failed trying to send Mattermost table"
                sys.exit(2)
            else:
                print >> sys.stderr, "INFO Mattermost table successfully sent"

    return return_value

if __name__ == "__main__":
    counter = 0
    for i in sys.argv:
        print >> sys.stderr, "INFO arg %s: %s" % (str(counter), str(i))
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        success = table_broker(payload)
        if not success:
            print >> sys.stderr, "FATAL Failed trying to send Mattermost notification"
            sys.exit(2)
        else:
            print >> sys.stderr, "INFO Mattermost notification successfully sent"
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
