import sys
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import gzip
import csv
import os

from fnmatch import fnmatch

# Create Markdown dialect for ligning up csv
csv.register_dialect("markdown", delimiter='|', escapechar='\\', quoting=csv.QUOTE_NONE, lineterminator='\n')

def send_log(output_file, message):
    print(message, file=output_file)

def delete_key(key, dic):
    if key in dic:
        del dic[key]
    return dic

def sanitize_results(data):
    header_to_delete = []

    for item in data:
        for v in item.keys():
            if '__mv_' in v or v == 'mvtime' or v == '_tc':
                header_to_delete.append(v)

    for item in header_to_delete:
        data = [delete_key(item, dic) for dic in data]
    return data

def sanitize_list(field_list):
    for item in field_list[:]:
        if '__mv_' in item or item == 'mvtime' or item == '_tc':
            field_list.remove(item)
    return field_list

def create_markdown_string(str_list, separator):
    if str_list[-1] == '':
        str_list = str_list[:-1]
    markdown_list = ['|' + i + '|' for i in str_list]
    markdown_list.insert(1, separator)
    return '\n'.join(markdown_list)

def create_markdown_separator(value_list):
    markdown_string = "|"
    for value in value_list:
        markdown_string += '-|'
    #markdown_string += '\n'
    send_log(sys.stderr, "DEBUG Markdown header length is %s" % str(value_list))
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
        send_log(sys.stderr, "DEBUG Filtering arg %s" % param)
        if '_field' in param:
            send_log(sys.stderr, "DEBUG Adding arg %s to field list" % param)
            field_list.append(value)

    attachment_dict['fields'] = field_list

    return attachment_dict
    
def send_notification(msg, url, attachment=None):
    send_log(sys.stderr, "INFO Sending message to Mattermost url %s" % (url))
    msg_limit = 4000
    if len(msg) > msg_limit:
        send_log(sys.stderr, "WARN Message is longer than limit of %d characters and will be truncated" % msg_limit)
        msg = msg[0:msg_limit - 3] + '...'
    data = dict(
        text=msg,
        icon_url='https://www.splunk.com/content/dam/splunk2/images/icons/favicons/mstile-150x150.png',
        username='Splunk Alert',
    )

    body = json.dumps(data)
    send_log(sys.stderr, 'DEBUG Calling url="%s" with body=%s' % (url, body))

    if attachment:
        data['attachments'] = [attachment]
        body = json.dumps(data)
        send_log(sys.stderr, 'DEBUG Adding attachment to body with body=%s' % (body))
    
    req = Request(url, body.encode('utf-8'), {"Content-Type": "application/json"})
    try:
        res = urlopen(req)
        body = res.read().decode('utf-8')
        send_log(sys.stderr, "INFO Mattermost server responded with HTTP status=%d" % res.code)
        send_log(sys.stderr, "DEBUG Mattermost server response: %s" % json.dumps(body))
        return 200 <= res.code < 300
    except HTTPError as e:
        send_log(sys.stderr, "ERROR Error sending message: %s (%s)" % (e, str(dir(e))))
        send_log(sys.stderr, "ERROR Server response: %s" % e.read())
        return False

def table_broker(payload):
    send_log(sys.stderr, "DEBUG Sending message with payload %s" % payload)
    settings = payload.get('configuration')
    send_log(sys.stderr, "DEBUG Sending message with settings %s" % settings)
    table = settings.get('table')
    msg = settings.get('message')
    url = settings.get('url')
    return_value = False
    if table:
        send_log(sys.stderr, "DEBUG Results found")
        results_file_location = payload.get('results_file')
        send_log(sys.stderr, "INFO Results at %s" % results_file_location)

        header_line = []
        data = []
        fieldnames = []
        results = []
        results_string = ""
        with gzip.open(results_file_location, 'rt') as results_file:
            results = csv.DictReader(results_file)
            fieldnames = results.fieldnames[:]
            data = sanitize_results(list(results))

        fieldnames = sanitize_list(fieldnames)
        markdown_separator = create_markdown_separator(fieldnames)
        with open('temp.csv', 'w+') as temp:
            writer = csv.DictWriter(temp, fieldnames=fieldnames, dialect="markdown")
            writer.writeheader()
            writer.writerows(data)
        
        with open('temp.csv', 'r') as temp:
            data = temp.read().split('\n')
            results_string = create_markdown_string(data, markdown_separator)

        if os.path.isfile('temp.csv'):
            os.remove('temp.csv')

        send_log(sys.stderr, "INFO Results markdown string: %s" % results_string)
        # Decide whether to send this info via table or attachment
        if table == "table":
            return_value = send_notification(msg, url)
            send_log(sys.stderr, "INFO Results table selected")

            table_return_value = send_notification(results_string, url)
            if not table_return_value:
                send_log(sys.stderr, "FATAL Failed trying to send Mattermost table")
                sys.exit(2)
            else:
                send_log(sys.stderr, "INFO Mattermost table successfully sent")

        elif table == "attach":
            send_log(sys.stderr, "INFO Results attachment selected")
            saved_search_name = payload.get('search_name')
            send_log(sys.stderr, "DEBUG Saved search name: %s" % saved_search_name)
            results_link = payload.get('results_link')
            send_log(sys.stderr, "DEBUG Results link: %s" % results_link)
            owner = payload.get('owner')
            author_name = owner
            send_log(sys.stderr, "DEBUG Search owner: %s" % owner)
            app = payload.get('app')
            send_log(sys.stderr, "DEBUG Search app context: %s" % app)
            # delete 2 because of header and separator
            count = len(data) - 2
            send_log(sys.stderr, "DEBUG Search result count: %s" % count)
            description = payload.get('description')
            send_log(sys.stderr, "DEBUG Search description: %s" % description)

            fallback = "Results generated by alert \"%s\"" % saved_search_name
            pretext = "Results in markdown table format. Search results in Splunk can be found [here](%s)." % results_link
            text = results_string
            title = "%s results" % saved_search_name
            app_field = create_mm_field("App", app, short=True)
            search_field = create_mm_field("Saved Search", saved_search_name, short=True)
            description_field = create_mm_field("Description", description, short=False)
            owner_field = create_mm_field("Owner", owner, short=True)
            count_field = create_mm_field("Results Count", count, short=True)
            results_field = create_mm_field("Results Link", results_link, short=False)
            #date_field = create_mm_field("Date Alerted", trigger_epoch_string, short=True)
            
            send_log(sys.stderr, "DEBUG Creating attachment dictionary")
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
            send_log(sys.stderr, "INFO Results table request had unexpected value %s" % table)
            return_value = send_notification(msg, url)

    else:
        send_log(sys.stderr, "INFO Results table request not found")
        return_value = send_notification(msg, url)
    return return_value

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        success = table_broker(payload)
        if not success:
            send_log(sys.stderr, "FATAL Failed trying to send Mattermost notification")
            sys.exit(2)
        else:
            send_log(sys.stderr, "INFO Mattermost notification successfully sent")
    else:
        send_log(sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
