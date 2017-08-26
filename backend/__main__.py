#! /usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.firebase_db_util import post_feed, get_last_feeds, get_reddit_url, update_desc, is_enabled, delete_feed
from backend.fcm_util import send_fcm
from backend.reddit_util import submit_to_reddit, edit_submission, delete_submission
from backend.scrape_util import format_text, scrape_site, smart_truncate
from backend.rss_util import parse_feed, find_feed_in_array
from backend.scopes import SCOPE_NEWS, SCOPE_UPLOADPLAN, SCOPE_PIETCAST, SCOPE_VIDEO
from backend.cloud_storage import store_image_in_gcloud, remove_image_from_gcloud
from backend.log_util import log

force = False
debug = False
limit = 6


def check_for_update(scope):
    # Check if master switch in db is off and abort if true
    if not is_enabled():
        if debug:
            log("Info", "Master switch is off, ignoring (debug)")
        else:
            log("Warning", "Master switch is off, aborting")
            return

    log("Checking for " + scope)
    website_feeds = parse_feed(scope, limit)
    if website_feeds is None:
        log("Error", "Pietsmiet.de feeds are empty, bad network? Aborting")
        return

    # Load more db items than new ones to compare better (e.g. if there are deleted items in the db)
    db_feed_limit = limit + 5
    db_feeds = get_last_feeds(scope, db_feed_limit)
    
    # Check that loading of db posts was successful
    if db_feeds is None:
        log("Error", "Cannot retrieve old feeds! Aborting")
        return
    # Check that there are posts in db, otherwise reload posts
    if db_feeds is False:
        log("Warning", "No feeds in db, loading all posts in db")
        fetch_and_store(scope, 25)
        return
    # Check that all posts were loaded, otherwise reload posts
    if len(db_feeds) is not db_feed_limit:
        log("Error", "Loaded " + str(len(db_feeds)) + " feeds from db, should be " + str(db_feed_limit))
        fetch_and_store(scope, 25)
        return

    # Iterate through every website feed and check if it is new (its title or link does _not_ match 
    # one of the old feeds)
    new_feeds = {}
    i = 0
    for website_feed in website_feeds:
        # Compare pietsmiet.de feed against all feeds from db
        if (find_feed_in_array(website_feed, db_feeds) is False) or force:
            new_feeds[i] = website_feed
        i += 1

    if (len(new_feeds) >= limit) and not force:
        # All feeds changed, means there was probably a gap inbetween => Reload all posts into db
        # This should only happen if the script wasn't running for a few days
        log("Posts in db too old, loading all posts in db")
        fetch_and_store(scope, 25)
    elif len(new_feeds) == 0:
        # No new posts found => Database should be the same as pietsmiet.de now,
        # so we can check if there are invalid posts in db
        log("Info", "No new posts found for scope " + scope)
        check_deleted_posts(db_feeds, website_feeds)

        if scope == SCOPE_UPLOADPLAN:
            # Also check if the uploadplan was edited
            website_feed = find_feed_in_array(db_feeds[0], website_feeds)
            if website_feed is not False:
                check_uploadplan_edited(db_feeds[0], website_feed)
    else:
        # Iterate through all new feeds and process them
        for i, new_feed in new_feeds.items():
            # New item found
            process_new_item(new_feed, scope, i)
            time.sleep(1)


def check_uploadplan_edited(old_feed, new_feed):
    # Check if uploadplan desc changed
    new_feed.desc = scrape_site(new_feed.link)
    if new_feed.desc != old_feed.desc:
        if debug:
            log("Desc has changed, not putting into db because of debug")
            return
        if old_feed.reddit_url is not None:
            edit_submission(format_text(new_feed), old_feed.reddit_url)
        else:
            # Inform about missing reddit url and still store the new desc to avoid spam of this
            log("Warning", "No reddit url provided")
        # Put the updated desc back into db
        update_desc(new_feed)


def check_deleted_posts(db_feeds, website_feeds):
    # Compare posts from db against the rss posts to make sure there are no deleted posts in the db
    i = 0
    for db_feed in db_feeds:
        i += 1
        is_deleted = True
        for website_feed in website_feeds:
            if (db_feed.title == website_feed.title) and (db_feed.date == website_feed.date) and (
                        db_feed.link == website_feed.link):
                is_deleted = False
                # We found the equivalent, break the loop
                break

        if is_deleted:
            # There was no equivalent on pietsmiet.de, means it was probably deleted
            # => Remove it from the database
            log("Feed with title '" + db_feed.title + "' was in db but not on pietsmiet.de. Deleting from database!")
            if not debug:
                delete_feed(db_feed)
                remove_image_from_gcloud(db_feed)
        # Only compare db posts against the same size of pietsmiet.de posts
        # because there are more db posts loaded than pietsmiet.de posts
        if i >= len(website_feeds):
            break


def process_new_item(feed, scope, i):
    # Submit to firebase FCM & DB and if uploadplan to reddit 
    log("Debug", "New item in " + feed.scope)
    if (scope == SCOPE_UPLOADPLAN) or (scope == SCOPE_NEWS):
        # Scrape site for the feed description
        feed.desc = scrape_site(feed.link)
    if scope == SCOPE_NEWS:
        # Truncate the news description
        feed.desc = smart_truncate(feed)
    
    if scope == SCOPE_VIDEO:
        if feed.image_url is not None:
            # Store thumb in gcloud and send fcm
            feed.image_url = store_image_in_gcloud(feed.image_url, feed)
            fcm_success = send_fcm(feed, debug)
        else: 
            # Don't send FCM as videos without thumbs are usually bad uploads and will be reuploaded
            # Still store it in the DB if it just doesn't have a thumb for another reason
            log("Warning", "No thumbnail found, means it's probably a bad upload. Not sending FCM!" + 
                    "Title is \"" + feed.title + "\"")
            fcm_success = True 
    else:
        fcm_success = send_fcm(feed, debug)

    if not fcm_success:
        log("Error", "Could not send FCM, aborting!")
        return

    if (scope == SCOPE_UPLOADPLAN) and (i == 0):
        # Don't submit old uploadplan: Only if it's the first new_feed and new, submit it
        log("Submitting uploadplan to reddit")
        time.sleep(1)
        r_url = submit_to_reddit(feed.title, format_text(feed), debug=debug)
        feed.reddit_url = r_url
    if not debug:
        post_feed(feed)


def fetch_and_store(scope, limit):
    website_feeds = parse_feed(scope, limit)
    log("Loading " + str(len(website_feeds)) + " items in " + scope)
    for feed in website_feeds:
        if (scope == SCOPE_UPLOADPLAN) or (scope == SCOPE_NEWS):
            feed.desc = scrape_site(feed.link)
            time.sleep(1)
        if scope == SCOPE_NEWS:
            feed.desc = smart_truncate(feed)
        if (scope == SCOPE_VIDEO) and (feed.image_url is not None):
            feed.image_url = store_image_in_gcloud(feed.image_url, feed)
        if debug:
            log ("Not posting to firebase because of debug")
        else:
            post_feed(feed)
        time.sleep(1)


parser = argparse.ArgumentParser()
parser.add_argument("-s", "--scope", required=False, choices=['uploadplan', 'news', 'video', 'pietcast', 'delete'],
    help="The scope to load")
parser.add_argument("-d", "--debug", required=False, default=False, action='store_true', 
    help="This enables debug mode, which is basically a dry run. It'll not update the firebase db" + 
            "and only submit FCMs to the debug channel and reddit posts to r/l3d00m")
parser.add_argument("-f", "--force", required=False, default=False, action='store_true', 
    help="This enables the dry run debug mode and simulates new posts even if there are no new posts.")
parser.add_argument("-a", "--loadall", required=False, type=int,
    help="(Re)loads the specified amount of posts in all scopes into the database. " + 
            "Note: Limit for uploadplan, pietcast and news is always 8")
parser.add_argument("-l", "--limit", required=False, type=int, choices=range(2, 20),
    help="Set a custom limit how many posts should be compared.")
args = parser.parse_args()

if args.debug:
    log("Debug enabled.")
    debug = True

if args.force:
    log("Debug and force enabled.")
    force = True
    debug = True

if args.limit:
    if args.loadall:
        log("Limit ignored because it's specified in the --loadall parameter")
    
    limit = int(args.limit)
    log("Info", "Limit set to " + str(limit))

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
