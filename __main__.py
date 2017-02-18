#! /usr/bin/python3
import time
import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from backend.firebase_util import send_fcm, put_feed_into_db
from backend.reddit_util import submit_to_reddit, edit_submission
from backend.scrape_util import format_text
from backend.rss_util import parse_feed, Feed
from backend.scopes import SCOPE_NEWS, SCOPE_UPLOADPLAN, SCOPE_PIETCAST

old_feed = None

def in_between_time(start_hour, end_hour):
    now = int(datetime.datetime.now().hour)
    if start_hour <= end_hour:
        return start_hour <= now < end_hour
    else:  # over midnight e.g., 23-04
        return start_hour <= now or now < end_hour


def write(text, filename):
    with open(filename, "w+") as text_file:
        print(text, file=text_file)


def read(filename):
    try:
        with open(filename, "r") as text_file:
            return text_file.read().rstrip()
    except Exception:
        print("No file created yet? ENOENT")
        return ""
		
		
def smart_truncate(content, link, length=220):
    if not len(content) <= length:
        content = content[:length].rsplit(' ', 1)[0] + '...  '
		
    return content + "<a href=\"" + link + "\">Auf pietsmiet.de weiterlesen <span>→</span></a>"


def check_for_update(scope):
    new_feed = parse_feed(scope)
    if (new_feed is None):
        return
    new_title = new_feed.title
    old_title = read(filename=scope)
    if (scope == SCOPE_UPLOADPLAN):
        compare_uploadplan(new_feed, old_title)
    if new_title != old_title:
        write(new_title, scope)            
        #elif scope == SCOPE_NEWS:
        #    new_feed.desc = smart_truncate(new_feed.desc, new_feed.link)
        #    submit_to_reddit("Neuer Post auf pietsmiet.de: " + new_feed.title, format_text(new_feed))
        put_feed_into_db(new_feed)
        send_fcm(new_feed)

def compare_uploadplan(new_feed, old_title):
    global old_feed
    if new_feed.title != old_title:
        old_feed = new_feed
        submit_to_reddit(new_feed.title, format_text(new_feed))
    elif (old_feed is not None) and (new_feed.desc != old_feed.desc):
        edit_submission(format_text(new_feed))
        

check_for_update(SCOPE_PIETCAST)
#check_for_update(SCOPE_NEWS)
check_for_update(SCOPE_UPLOADPLAN)

while 1:
    # Check for updates:
    # 1) PietCast
    # 2) Between 9am and 1pm for Uploadplan
    # 3) News on pietsmiet.de
    # (I'm two lazy to do it asynchronous)
    i = 0
    if in_between_time(10, 15):
        check_for_update(SCOPE_UPLOADPLAN)

    if (i == 4) or (i == 9) or (i == 14):
        check_for_update(SCOPE_PIETCAST)
        #check_for_update(SCOPE_NEWS)
    if i == 14:
        i = 0

    i += 1

    time.sleep(1800)

