#! /usr/bin/python3
# -*- coding: utf-8 -*-
import time
import datetime
import sys
import os
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from backend.firebase_util import send_fcm, put_feed_into_db
from backend.reddit_util import submit_to_reddit, edit_submission, delete_submission
from backend.scrape_util import format_text, smart_truncate
from backend.rss_util import parse_feed
from backend.scopes import SCOPE_NEWS, SCOPE_UPLOADPLAN, SCOPE_PIETCAST, SCOPE_VIDEO
from backend.querys import write_feed, get_last_feed, insert_reddit_url, get_reddit_url
		
force = False

def check_for_update(scope):
    global force
    print("Checking for: " + scope)
    new_feed = parse_feed(scope)
    if (new_feed is None):
        print("Feed is empty, bad network?")
        return
    old_feed = get_last_feed(scope)
    if (scope == SCOPE_UPLOADPLAN):
        compare_uploadplan(new_feed, old_feed)
    if (force) or (old_feed is None) or (new_feed.title != old_feed.title):
        print("New item in " + scope)
        write_feed(new_feed)            
        #if scope == SCOPE_NEWS:
            #new_feed.desc = smart_truncate(new_feed.desc, new_feed.link)
            #submit_to_reddit("Neuer Post auf pietsmiet.de: " + new_feed.title, format_text(new_feed))
        put_feed_into_db(new_feed)
        send_fcm(new_feed)

def compare_uploadplan(new_feed, old_feed):
    global force    
    if (force) or (old_feed is None) or (new_feed.title != old_feed.title):
        print("Submitting uploadplan to reddit")
        submission_url = submit_to_reddit(new_feed.title, format_text(new_feed))
        insert_reddit_url(submission_url)
    elif new_feed.desc != old_feed.desc:
        print("Desc is different")
        edit_submission(format_text(new_feed), submission_url)
        

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--scope", required=True)
parser.add_argument("-f", "--force", required=False, default=False, action='store_true')
args = vars(parser.parse_args())

if args['force']:
    force = True

if args['scope'] == 'uploadplan':
    check_for_update(SCOPE_UPLOADPLAN)

if args['scope'] == 'video':   
    check_for_update(SCOPE_VIDEO)
    
if args['scope'] == 'pietcast':
    check_for_update(SCOPE_PIETCAST)

if args['scope'] == 'news':
    check_for_update(SCOPE_NEWS)

if args['scope'] == 'delete':
    url = get_reddit_url()
    if url is not None:
        print("Deleting submission...")
        delete_submission(url)
    else:
        print("Couldn't delete submission, no URL in db")
        
print("finished")
