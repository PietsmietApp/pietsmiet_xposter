#! /usr/bin/python3
# -*- coding: utf-8 -*-

# Current cron entries:
# */15 9-12 * * * python3 /home/pi/backend -s uploadplan >/home/pi/crontab.log 2>&1
# 0 12-17 * * * python3 /home/pi/backend -s uploadplan >/home/pi/crontab.log 2>&1
# 2,32 11-22 * * * python3 /home/pi/backend -s video >/home/pi/crontab.log 2>&1
# 0 11-24/3 * * * python3 /home/pi/backend -s news >/home/pi/crontab.log 2>&1
# 0 11-24/3 * * * python3 /home/pi/backend -s pietcast >/home/pi/crontab.log 2>&1
#
# => durschnittlich ~2 Aufrufe pro Stunde, unabhängig von der Anzahl Nutzer
import time
import datetime
import sys
import os
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from backend.firebase_util import send_fcm, put_feed, get_feed, put_reddit_url, get_reddit_url
from backend.reddit_util import submit_to_reddit, edit_submission, delete_submission
from backend.scrape_util import format_text, smart_truncate
from backend.rss_util import parse_feed
from backend.scopes import SCOPE_NEWS, SCOPE_UPLOADPLAN, SCOPE_PIETCAST, SCOPE_VIDEO
		
force = False
debug = False

def check_for_update(scope):
    print("Checking for: " + scope)
    new_feed = parse_feed(scope)
    if (new_feed is None):
        print("Feed is empty, bad network?")
        return
    old_feed = get_feed(scope)
    if(old_feed is None):
        print("Error: Cannot retrieve old feed! Aborting")
        return
    if (force) or (new_feed.title != old_feed.title):
        print("New item in " + scope)       
        put_feed(new_feed)
        send_fcm(new_feed, debug)
    if (scope == SCOPE_UPLOADPLAN): # or (scope == SCOPE_NEWS)
        compare_uploadplan(new_feed, old_feed)

def compare_uploadplan(new_feed, old_feed):   
    if (force) or (new_feed.title != old_feed.title):
        print("Submitting uploadplan to reddit")
        #if new_feed.scope == SCOPE_NEWS:
            #new_feed.desc = smart_truncate(new_feed.desc, new_feed.link)
            #submit_to_reddit("Neuer Post auf pietsmiet.de: " + new_feed.title, format_text(new_feed))
        #else:
        submission_url = submit_to_reddit(new_feed.title, format_text(new_feed), debug=debug)
        put_reddit_url(submission_url)
    elif new_feed.desc != old_feed.desc:
        print("Desc is different")
        new_feed.reddit_url = old_feed.reddit_url
        put_feed(new_feed)
        if (old_feed.reddit_url is not None):
            edit_submission(format_text(new_feed), old_feed.reddit_url)
        else:
            print("No reddit url provided")
        

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--scope", required=True)
parser.add_argument("-f", "--force", required=False, default=False, action='store_true')
parser.add_argument("-d", "--debug", required=False, default=False, action='store_true')
args = parser.parse_args()

if args.force:
    force = True

if args.debug:
    debug = True

if args.scope == 'uploadplan':
    check_for_update(SCOPE_UPLOADPLAN)
elif args.scope == 'video':   
    check_for_update(SCOPE_VIDEO)
elif args.scope == 'pietcast':
    check_for_update(SCOPE_PIETCAST)
elif args.scope == 'news':
    check_for_update(SCOPE_NEWS)
elif args.scope == 'delete':
    url = get_reddit_url()
    if url is not None:
        print("Deleting submission...")
        delete_submission(url)
    else:
        print("Couldn't delete submission, no URL in db")
else:      
    print("No valid scope (uploadplan, news, video, delete, pietcast) supplied!")
