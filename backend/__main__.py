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

from backend.firebase_db_util import post_feed, get_last_feeds, get_reddit_url, update_desc, is_enabled, delete_feed
from backend.fcm_util import send_fcm
from backend.reddit_util import submit_to_reddit, edit_submission, delete_submission
from backend.scrape_util import format_text, scrape_site, smart_truncate
from backend.rss_util import parse_feed
from backend.scopes import SCOPE_NEWS, SCOPE_UPLOADPLAN, SCOPE_PIETCAST, SCOPE_VIDEO
from backend.cloud_storage import store_image_in_gcloud, remove_image_from_gcloud
from backend.log_util import log

force = False
debug = False
limit = 5


def check_for_update(scope):
    # Check if master switch in db is off and abort if true
    if not is_enabled():
        log("Error", "Master switch is off, aborting")
        return

    log("Checking for: " + scope)
    new_feeds = parse_feed(scope, limit)
    if new_feeds is None:
        log("Error", "Pietsmiet.de feeds are empty, bad network? Aborting")
        return

    # Load more old items than new ones to compare better (e.g. if there are deleted items in the db)
    old_feeds = get_last_feeds(scope, limit + 5)
    if old_feeds is None:
        log("Error", "Cannot retrieve old feeds! Aborting")
        return
    elif old_feeds is False:
        log("Warning", "No feeds in db, loading all posts in db")
        fetch_and_store(scope, 25)

    # Iterate through every new feed and check if it (=> its title and link) matches one of the old feeds
    is_completely_new = True
    i = 0
    for new_feed in new_feeds:
        different = False
        for old_feed in old_feeds:
            if (new_feed.title == old_feed.title) or (new_feed.link == old_feed.link):
                different = old_feed
                is_completely_new = False
                # We found the equivalent, break the loop
                break

        if not different or force:
            # New item found
            process_new_item(new_feed, scope, i)
            time.sleep(2)
        else:
            # => This post was already in db

            if i == 0:
                # No new posts found this time
                # Means we can check if there are invalid posts in db and if the uploadplan was edited

                check_deleted_posts(old_feeds, new_feeds)
                if scope == SCOPE_UPLOADPLAN:
                    check_uploadplan_edited(different, new_feed)

            # Don't iterate through older posts from rss if a single post inbetween was not new
            # This is to prevent fcm spam on possible bugs (if there are other items in the same db)
            break

        i += 1

    if is_completely_new and not force:
        # All feeds changed, means there was probably a gap inbetween => Reload all posts into db
        # This only happens if the script wasn't running for a few days
        log("Posts in db too old, loading all posts in db")
        fetch_and_store(scope, 15)


def check_uploadplan_edited(old_feed, new_feed):
    # Check if uploadplan desc changed if scope is uploadplan
    new_feed.desc = scrape_site(new_feed.link)
    if new_feed.desc != old_feed.desc:
        if old_feed.reddit_url is not None:
            edit_submission(format_text(new_feed), old_feed.reddit_url)
        else:
            log("Warning", "No reddit url provided")
        # Put the updated desc back into db
        update_desc(new_feed)


def check_deleted_posts(old_feeds, new_feeds):
    # Compare posts from db against the rss posts to make sure there are no deleted posts in the db
    i = 0
    for old_feed in old_feeds:
        i += 1
        is_deleted = True
        for new_feed in new_feeds:
            if (old_feed.title == new_feed.title) and (old_feed.date == new_feed.date) and (
                        old_feed.link == new_feed.link):
                is_deleted = False
                # We found the equivalent, break the loop
                break

        if is_deleted:
            # There was no equivalent on pietsmiet.de, means it was probably deleted
            # => Remove it from the database
            log("Feed with title '" + old_feed.title.encode('unicode_escape').decode('latin-1', 'ignore') +
                "' was in db but not on pietsmiet.de. Deleting from database!")
            if not debug:
                delete_feed(old_feed)
                remove_image_from_gcloud(old_feed)
        # Only compare db posts against the same size of pietsmiet.de posts
        # because there are more db posts loaded than pietsmiet.de posts
        if i >= len(new_feeds):
            break


def process_new_item(new_feed, scope, i):
    # Submit to firebase FCM & DB and if uploadplan to reddit 
    log("Debug", "New item in " + new_feed.scope)
    if (scope == SCOPE_UPLOADPLAN) or (scope == SCOPE_NEWS):
        # Scrape site for the feed description
        new_feed.desc = scrape_site(new_feed.link)
    if scope == SCOPE_NEWS:
        # Truncrate the news description
        new_feed.desc = smart_truncate(new_feed)
    if (scope == SCOPE_VIDEO) and (new_feed.image_url is not None):
        new_feed.image_url = store_image_in_gcloud(new_feed.image_url, feed)

    fcm_success = send_fcm(new_feed, debug)
    if not fcm_success:
        log("Error", "Could not send FCM, aborting!")

    if (scope == SCOPE_UPLOADPLAN) and (i == 0):
        # Don't submit old uploadplan: Only if it's the first new_feed and new, submit it
        log("Submitting uploadplan to reddit")
        time.sleep(1)
        r_url = submit_to_reddit(new_feed.title, format_text(new_feed), debug=debug)
        if not debug:
            new_feed.reddit_url = r_url

    post_feed(new_feed)


def fetch_and_store(scope, limit):
    new_feeds = parse_feed(scope, limit)
    log("Loading " + str(len(new_feeds)) + " items in " + scope)
    for feed in new_feeds:
        if (scope == SCOPE_UPLOADPLAN) or (scope == SCOPE_NEWS):
            feed.desc = scrape_site(feed.link)
            time.sleep(1)
        if scope == SCOPE_NEWS:
            feed.desc = smart_truncate(feed)
        if (scope == SCOPE_VIDEO) and (feed.image_url is not None):
            feed.image_url = store_image_in_gcloud(feed.image_url, feed)
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
        log("Error", "Force can only be used in debug mode (-d flag)")
        sys.exit()

if args.loadall:
    log("Loading all items to db. This will take a few minutes")
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
        log("Deleting submission...")
        delete_submission(url)
    else:
        log("Warning", "Couldn't delete submission, no URL in db")
else:
    log("Error", "No valid scope (--scope [uploadplan, news, video, delete, pietcast]) supplied!")
