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
# => durschnittlich ~2 Aufrufe pro Stunde, unabhängig von der Anzahl Nutzer
import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.firebase_util import send_fcm, post_feed, get_last_feeds, get_reddit_url, update_desc
from backend.reddit_util import submit_to_reddit, edit_submission, delete_submission
from backend.scrape_util import format_text, scrape_site
from backend.rss_util import parse_feed
from backend.scopes import SCOPE_NEWS, SCOPE_UPLOADPLAN, SCOPE_PIETCAST, SCOPE_VIDEO

force = False
debug = False


def check_for_update(scope):
    print("Checking for: " + scope)
    new_feeds = parse_feed(scope)
    if new_feeds is None:
        print("New Feeds are empty, bad network?")
        return

    old_feeds = get_last_feeds(scope)
    if old_feeds is None:
        print("Error: Cannot retrieve old feeds! Aborting")
        return

    # Iterate through every new feed and check if it matches one of the old feeds
    i = 0
    for new_feed in new_feeds:
        new = True
        if old_feeds != False:
            for old_feed in old_feeds:
                if (new_feed.title == old_feed.title) and (new_feed.date == old_feed.date):
                    # does match old feed => is not new
                    new = False

        if new or force:
            # Is new => Submit to firebase FCM & DB and if uploadplan to reddit 
            print("New item in " + new_feed.scope)
            if (scope == SCOPE_UPLOADPLAN) or (scope == SCOPE_NEWS):
                new_feed.desc = scrape_site(new_feed.link)

            # If it's the first new_feed and new, submit it
            if (scope == SCOPE_UPLOADPLAN) and i == 0:
                print("Submitting uploadplan to reddit")
                new_feed.reddit_url = submit_to_reddit(new_feed.title, format_text(new_feed), debug=debug)
                send_fcm(new_feed, debug)
            else:
                # Don't submit old uploadplan
                send_fcm(new_feed, debug)
            post_feed(new_feed)
        elif scope == SCOPE_UPLOADPLAN and i == 0:
            # Check if desc changed if scope is uploadplan and it's the first new_feed
            new_feed.desc = scrape_site(new_feed.link)
            if new_feed.desc != old_feed.desc:
                print("Desc is different")
                if old_feed.reddit_url is not None:
                    new_feed.reddit_url = old_feed.reddit_url
                    edit_submission(format_text(new_feed), old_feed.reddit_url)
                else:
                    print("No reddit url provided")
                    # Put the updated desc back into db
                update_desc(new_feed)
        i = i + 1


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
