#! /usr/bin/python3
# -*- coding: utf-8 -*-

# Current cron entries:
# */15 9-12 * * * python3 /home/pi/backend -s uploadplan >/home/pi/crontab.log 2>&1
# 0 12-17 * * * python3 /home/pi/backend -s uploadplan >/home/pi/crontab.log 2>&1
# 2,32 11-22 * * * python3 /home/pi/backend -s video >/home/pi/crontab.log 2>&1
# 0 11-24/3 * * * python3 /home/pi/backend -s news >/home/pi/crontab.log 2>&1
# 0 11-24/3 * * * python3 /home/pi/backend -s pietcast >/home/pi/crontab.log 2>&1
# 0 3 * * * python3 /home/pi/backend -s delete >/home/pi/crontab.log 2>&1
#
# => durchschnittlich ~2 Aufrufe pro Stunde, unabhängig von der Anzahl Nutzer
import argparse
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.firebase_db_util import post_feed, get_last_feeds, get_reddit_url, update_desc, is_enabled
from backend.fcm_util import send_fcm
from backend.reddit_util import submit_to_reddit, edit_submission, delete_submission
from backend.scrape_util import format_text, scrape_site, smart_truncate
from backend.rss_util import parse_feed
from backend.scopes import SCOPE_NEWS, SCOPE_UPLOADPLAN, SCOPE_PIETCAST, SCOPE_VIDEO

force = False
debug = False


def check_for_update(scope):
    if not is_enabled():
        print("Master switch is off, aborting")
        return
        
    limit = 4
    print("Checking for: " + scope)
    new_feeds = parse_feed(scope, limit)
    if new_feeds is None:
        print("New Feeds are empty, bad network?")
        return

    # Load more old items to compare
    old_feeds = get_last_feeds(scope, limit + 10)
    if old_feeds is None:
        print("Error: Cannot retrieve old feeds! Aborting")
        return
    elif old_feeds is False:
        print("No feeds in db, loading all posts in db")
        fetch_and_store(scope, 25)
       

    # Iterate through every new feed and check if it matches one of the old feeds
    is_completely_new = True
    i = 0
    for new_feed in new_feeds:
        different = False
        for old_feed in old_feeds:
            if new_feed.title == old_feed.title:
                different = old_feed
                is_completely_new = False
                # We found the equivalent, break the loop
                break
        
        if not different or force:
            # Is new => Submit to firebase FCM & DB and if uploadplan to reddit 
            print("New item in " + new_feed.scope)
            if (scope == SCOPE_UPLOADPLAN) or (scope == SCOPE_NEWS):
                new_feed.desc = scrape_site(new_feed.link)
            if (scope == SCOPE_NEWS):
                new_feed.desc = smart_truncate(new_feed)
                
            fcm_success = send_fcm(new_feed, debug)
            if not fcm_success:
                print("CRTICAL ERROR: Could not send FCM, aborting!")

            # If it's the first new_feed and new, submit it => Don't submit old uploadplan
            if (scope == SCOPE_UPLOADPLAN) and i == 0:
                print("Submitting uploadplan to reddit")
                time.sleep(1)
                url = submit_to_reddit(new_feed.title, format_text(new_feed), debug=debug)
                if not debug:
                    new_feed.reddit_url = url
 
            post_feed(new_feed)
            time.sleep(2)
            
        elif scope == SCOPE_UPLOADPLAN and i == 0:
            old_feed = different
            # Check if desc changed if scope is uploadplan and it's the first new_feed
            new_feed.desc = scrape_site(new_feed.link)
            if new_feed.desc != old_feed.desc:
                if old_feed.reddit_url is not None:
                    edit_submission(format_text(new_feed), old_feed.reddit_url)
                else:
                    print("No reddit url provided")
                # Put the updated desc back into db
                update_desc(new_feed)
        else:
            # Don't iterate through older posts from rss after a single post inbetween was not new
            # This is to prevent fcm spam on possible bugs
            break
        
            
        i += 1
        
    if is_completely_new and not force:
        # All feeds changed, means there was a gap inbetween => Reload all posts into db
        # This only happens if the script wasn't running for a few days
        print("Posts in db too old, loading all posts in db")
        fetch_and_store(scope, 15)


def fetch_and_store(scope, limit):
    new_feeds = parse_feed(scope, limit)
    print("Loading " + str(len(new_feeds)) + " items in " + scope)
    for feed in new_feeds:
        if (scope == SCOPE_UPLOADPLAN) or (scope == SCOPE_NEWS):
            feed.desc = scrape_site(feed.link)
            time.sleep(3)
        if (scope == SCOPE_NEWS):
            feed.desc = smart_truncate(feed)
        post_feed(feed)
        time.sleep(1)


parser = argparse.ArgumentParser()
parser.add_argument("-s", "--scope", required=False)
parser.add_argument("-f", "--force", required=False, default=False, action='store_true')
parser.add_argument("-d", "--debug", required=False, default=False, action='store_true')
parser.add_argument("-l", "--loadall", required=False)
args = parser.parse_args()

if args.debug:
    debug = True
    
if args.force:
    if debug:
        force = True
    else:
        print("Force can only be used in debug mode (-d flag)")
        sys.exit()
    
if args.loadall:
    print("Loading all items to db. This will take a few minutes")
    limit = int(args.loadall)
    fetch_and_store(SCOPE_UPLOADPLAN, limit)
    fetch_and_store(SCOPE_NEWS, limit)
    fetch_and_store(SCOPE_VIDEO, limit)
    fetch_and_store(SCOPE_PIETCAST, limit)
    sys.exit()

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
    print("No valid scope (--scope [uploadplan, news, video, delete, pietcast]) supplied!")
