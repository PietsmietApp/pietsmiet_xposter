import re

from firebase import firebase

from backend.api_keys import fb_db_key, fb_db_url
from backend.rss_util import Feed
from backend.log_util import log

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
            "reddit_url": feed.reddit_url,
            "image_url": feed.image_url
        }
        firebase_db.put(url="/new/" + scope, name=name, data=data)
    except Exception as e:
        log('Error putting feed into fb db' + format(e))


def get_last_feeds(scope, limit):
    try:
        result = firebase_db.get("/new/" + scope, None, params={'orderBy': '"date"', 'limitToLast': limit})
    except Exception as e:
        log('Error getting feed from fb db' + format(e))
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
            log("Warning: Title not in db!")
        if 'desc' in feed:
            desc = feed['desc']
        elif scope != "video":
            log("Warning: Desc not in db!")
        if 'link' in feed:
            link = feed['link']
        else:
            log("Warning: Link not in db!")
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
    old_feeds.sort(key=lambda x: x.date, reverse=True)
    return old_feeds


def update_desc(feed):
    name = get_id_of_feed(feed)
    try:
        result = firebase_db.put("/new/uploadplan/" + name, "desc", data=feed.desc)
    except Exception as e:
        log("Warning", "Failed to update feed desc: " + format(e))
        result = None

    return result


def get_reddit_url():
    try:
        result = firebase_db.get("/new/uploadplan", None, params={'orderBy': '"date"', 'limitToLast': '1'})
        for key, feed in result.items():
            if 'reddit_url' in feed:
                return feed['reddit_url']
            else:
                log("No reddit url in result")
    except Exception as e:
        log('Error getting reddit url feed from fb db' + format(e))

    return None


def is_enabled():
    # Master switch to disable bot remotely
    try:
        result = firebase_db.get("/", "active")
        if result is not None:
            return result
    except Exception as e:
        log('Error getting active status from fb db' + format(e))

    return False


def delete_feed(feed):
    try:
        firebase_db.delete('/new/' + feed.scope, get_id_of_feed(feed))
        log('Feed deleted')
    except Exception as e:
        log('Error deleting feed from fb db' + format(e))


def get_id_of_feed(feed):
    title = re.sub(r'[^a-zA-Z0-9]+', '', feed.title)
    return str(feed.date) + title[:100]
