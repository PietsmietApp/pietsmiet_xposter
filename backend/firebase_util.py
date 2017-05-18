import re
import time
import math

from firebase import firebase
from pyfcm import FCMNotification
import pyfcm

from backend.api_keys import fcm_key, fb_db_key, fb_db_url
from backend.rss_util import Feed

firebase_fcm = FCMNotification(api_key=fcm_key)
authentication = firebase.FirebaseAuthentication(fb_db_key, None)
firebase_db = firebase.FirebaseApplication(fb_db_url, authentication=authentication)


def post_feed(feed):
    """
    Stores the content of the Feed object in firebase database
    :param feed: the feed object
    :return: None
    """
    scope = feed.scope
    try:
        name = get_id_of_feed(feed)
        data = {
            "desc": feed.desc,
            "link": feed.link,
            "title": feed.title,
            "date": feed.date,
            "scope": feed.scope,
            "reddit_url": feed.reddit_url
        }
        firebase_db.put(url="/new/" + scope, name=name, data=data)
    except Exception as e:
        print('Error putting feed into fb db' + format(e))


def get_last_feeds(scope, limit):
    try:
        result = firebase_db.get("/new/" + scope, None, params={'orderBy': '"date"', 'limitToLast': limit})
    except Exception as e:
        print('Error getting feed from fb db' + format(e))
        return None

    if result is None:
        return False
    old_feeds = []
    for key, feed in result.items():
        title = None
        desc = None
        link = None
        date = None
        reddit_url = None
        if 'title' in feed:
            title = feed['title']
        else:
            print("Warning: Title not in db!")
        if 'desc' in feed:
            desc = feed['desc']
        elif scope != "video":
            print("Warning: Desc not in db!")
        if 'link' in feed:
            link = feed['link']
        else:
            print("Warning: Link not in db!")
        if 'date' in feed:
            date = feed['date']
        if 'reddit_url' in feed:
            reddit_url = feed['reddit_url']
        old_feeds.append(Feed(scope=scope,
                              title=title,
                              desc=desc,
                              link=link,
                              date=date,
                              reddit_url=reddit_url))

    return old_feeds


def update_desc(feed):
    name = get_id_of_feed(feed)
    try:
        result = firebase_db.put("/new/uploadplan/" + name, "desc", data=feed.desc)
    except Exception as e:
        print('Error updating feed desc: ' + format(e))
        result = None

    return result


def get_reddit_url():
    try:
        result = firebase_db.get("/new/uploadplan", None, params={'orderBy': '"date"', 'limitToLast': '1'})
    except Exception as e:
        print('Error getting reddit url feed from fb db' + format(e))
        
    for key, feed in result.items():
        if 'reddit_url' in feed:
            return feed['reddit_url']
        else:
            print("No reddit url in result")

    return None
    

def is_enabled():
    # Master switch to disable bot remotely
    try:
        result = firebase_db.get("/", "active")
        if result is not None:
            return result
    except Exception as e:
        print('Error getting active status from fb db' + format(e))
        
    return False
    

def send_fcm(feed, debug=False):
    global firebase_fcm
    message = feed.desc
    title = feed.title
    game = None
    if feed.scope == "uploadplan":
        
        # Only send the actual uploadplan
        match = re.search("(?:<p>)?(?:<strong>)?Upload-Plan am.*?(?:</strong>)?(?:<p>|<br ?/?>)(.*?)(?:<br ?/?>)*<\/p>", feed.desc,
                          re.DOTALL)
        if match is not None:
            message = match.group(1)
    elif feed.scope == "video":
        # Only send the title of the video (as message)
        title = "Neues Video (pietsmiet.de)"
        message = feed.title
        if (u'\U0001f3ae' in message) or ('|' in message):
            # Check which game this is
            match = re.search("(?:\U0001F3AE|\|) ?(.*)", message)
            if match is not None:
                complete_game = match.group(1)
                game = re.sub(r" ?# ?\d+ ?", "", complete_game).encode('unicode_escape').decode('latin-1', 'ignore')
        else:
            game = "vlog"
        
    elif feed.scope == "news":
        # Only send the title of the news item (as message)
        title = "News (pietsmiet.de)"
        message = feed.title
        
    if debug:
        title = "DEBUG: " + title

    data_message = {
        "title": title,
        "topic": feed.scope,
        "message": message,
        "link": feed.link,
        "game": game
    }
    topic = feed.scope
    low_priority = True
    if debug is True:
        topic = "test"
        low_priority = False

    retry_count = 1
    
    while retry_count <= 3:
        try:
            firebase_fcm.notify_topic_subscribers(data_message=data_message, 
                topic_name=topic, 
                time_to_live=86400, 
                low_priority=low_priority)
            print("Sent fcm for " + feed.scope + " to topic/" + topic + 
                " with content: " + message.encode('unicode_escape').decode('latin-1', 'ignore'))
            return True
        except pyfcm.errors.FCMServerError as e:
            retry_time = pow(4, retry_count)
            print("Firebase servers are asleep, new try in " + str(retry_time) + " seconds." + 
                "\n Exception is: " + format(e))
            time.sleep(retry_time)
            firebase_fcm = FCMNotification(api_key=fcm_key)
            retry_count += 1
            
    return False


def get_id_of_feed(feed):
    title = re.sub(r'[^a-zA-Z0-9]+', '', feed.title)
    return str(feed.date) + title
