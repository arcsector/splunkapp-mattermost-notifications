import sys
import json
import urllib2
import gzip
import csv
import datetime
import os

from fnmatch import fnmatch

def sanitize_results(header_line, data):
    index_to_delete = []
    for header in header_line[:]:
        if '__mv_' in header or header == 'mvtime':
            index_to_delete.append(header_line.index(header))
            header_line.remove(header)
    for item in data[:]:
        data[data.index(item)] = list(set(data[data.index(item)]) - set([item.pop(index) for index in index_to_delete]))
    return header_line, data

def create_markdown_string(value_list):
    return '|' + '|'.join(value_list) + '|\n'

def create_markdown_separator(value_list):
    markdown_string = "|"
    for value in value_list:
        markdown_string += '-|'
    markdown_string += '\n'
    print >> sys.stderr, "DEBUG Markdown header length is %s" % str(value_list)
    return markdown_string

def create_mm_field(title, value, short=None):
    field_dict = {
        "title": title,
        "value": value
    }
    if short:
        field_dict['short'] = short
    return field_dict

def create_attachment_dict(fallback, pretext, text, title, author_name, **kwargs):
    attachment_dict = {
        "fallback": fallback,
        "pretext": pretext,
        "text": text,
        "title": title,
        "author_name": author_name
    }
    field_list = []

    for (param, value) in kwargs.items():
        print >> sys.stderr, "DEBUG Filtering arg %s" % param
        if '_field' in param:
            print >> sys.stderr, "DEBUG Adding arg %s to field list" % param
            field_list.append(value)

    attachment_dict['fields'] = field_list

    return attachment_dict
    
def send_notification(msg, url, attachment=None):
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

    if attachment:
        data['attachments'] = [attachment]
        body = json.dumps(data)
        print >> sys.stderr, 'DEBUG Adding attachment to body with body=%s' % (body)
    
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
    print >> sys.stderr, "DEBUG Sending message with payload %s" % payload
    settings = payload.get('configuration')
    print >> sys.stderr, "DEBUG Sending message with settings %s" % settings
    table = settings.get('table')
    msg = settings.get('message')
    url = settings.get('url')
    return_value = False
    if table:
        print >> sys.stderr, "DEBUG Results found"
        results_file_location = payload.get('results_file')
        print >> sys.stderr, "INFO Results at %s" % results_file_location

	data = []
        results_string = ""
        with gzip.open(results_file_location, 'rb') as results_file:
            results = csv.reader(results_file)
            header_line = next(results)
            data = list(results)
            header_line, data = sanitize_results(header_line, data)
            results_string = create_markdown_string(header_line)
            results_string += create_markdown_separator(header_line)
            results_string += ''.join([create_markdown_string(line) for line in data])
	print >> sys.stderr, "DEBUG Results markdown string: %s" % results_string
        # Decide whether to send this info via table or attachment
        if table == "table":
            return_value = send_notification(msg, url)
            print >> sys.stderr, "INFO Results table selected"

            table_return_value = send_notification(results_string, url)
            if not table_return_value:
                print >> sys.stderr, "FATAL Failed trying to send Mattermost table"
                sys.exit(2)
            else:
                print >> sys.stderr, "INFO Mattermost table successfully sent"

        elif table == "attach":
            print >> sys.stderr, "INFO Results attachment selected"
            saved_search_name = payload.get('search_name')
            print >> sys.stderr, "DEBUG Saved search name: %s" % saved_search_name
            results_link = payload.get('results_link')
            print >> sys.stderr, "DEBUG Results link: %s" % results_link
            owner = payload.get('owner')
            author_name = owner
            print >> sys.stderr, "DEBUG Search owner: %s" % owner
            app = payload.get('app')
            print >> sys.stderr, "DEBUG Search app context: %s" % app
            count = len(data)
            print >> sys.stderr, "DEBUG Search result count: %s" % count
            #trigger_time = payload.get('trigger_time')
            #print >> sys.stderr, "DEBUG Trigger time: %s" % trigger_time
            #trigger_date = payload.get('trigger_date')
            #print >> sys.stderr, "DEBUG Trigger date: %s" % trigger_date
            #trigger_epoch = payload.get('trigger_epoch')
            #print >> sys.stderr, "INFO Trigger epoch: %s" % trigger_epoch
            #trigger_epoch_value = datetime.datetime.fromtimestamp(float(trigger_epoch))
            #trigger_epoch_string = trigger_epoch_string.strftime('%Y-%m-%d %H:%M:%S')
            #print >> sys.stderr, "DEBUG Trigger epoch string: %s" % trigger_epoch_string
            description = payload.get('description')
            print >> sys.stderr, "DEBUG Search description: %s" % description

            fallback = "Results generated by alert \"%s\"" % saved_search_name
            pretext = "Results in CSV format. Search results in Splunk can be found [here](%s)." % results_link
            text = results_string
            title = "%s results" % saved_search_name
            app_field = create_mm_field("App", app, short=True)
            search_field = create_mm_field("Saved Search", saved_search_name, short=True)
            description_field = create_mm_field("Description", description, short=False)
            owner_field = create_mm_field("Owner", owner, short=True)
            count_field = create_mm_field("Results Count", count, short=True)
            results_field = create_mm_field("Results Link", results_link, short=False)
            #date_field = create_mm_field("Date Alerted", trigger_epoch_string, short=True)
            
            print >> sys.stderr, "DEBUG Creating attachment dictionary"
            attachment_dict = create_attachment_dict(
                fallback,
                pretext,
                text,
                title,
                author_name,
                app_field=app_field,
                search_field=search_field,
                description_field=description_field,
                owner_field=owner_field,
                count_field=count_field,
                results_field=results_field
            #    date_field
            )
            
            return_value = send_notification(msg, url, attachment_dict)

    else:
        print >> sys.stderr, "WARN Results table not found"
    return return_value

if __name__ == "__main__":
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
