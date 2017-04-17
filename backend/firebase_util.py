from backend.api_keys import fcm_key, fb_db_key, fb_db_url
from backend.rss_util import Feed
from pyfcm import FCMNotification
from firebase import firebase
import re

firebase_fcm = FCMNotification(api_key=fcm_key)
firebase_db = firebase.FirebaseApplication(fb_db_url, authentication=fb_db_key)


def put_feed(feed):
    """
    Stores the content of the Feed object in firebase database
    :param feed: the feed object
    :return: None
    """
    scope = feed.scope
    try:
        firebase_db.put(url="/" + scope, name="desc", data=feed.desc)
        firebase_db.put(url="/" + scope, name="link", data=feed.link)
        firebase_db.put(url="/" + scope, name="title", data=feed.title)
        firebase_db.put(url="/" + scope, name="date", data=feed.date)
    except Exception as e:
        print('Error putting feed into fb db' + format(e))


def get_feed(scope):
    try:
        result = firebase_db.get("/" + scope, None)
    except Exception as e:
        print('Error getting feed from fb db' + format(e))
        return None

    if result is None:
        return Feed(scope=scope, title='none_title')
        
    title = None
    desc = None
    link = None
    date = None
    reddit_url = None
    if 'title' in result:
        title = result['title']
    else:
        print("Warning: Title not in db!")
    if 'desc' in result:
        desc = result['desc']
    else:
        print("Warning: Desc not in db!")
    if 'link' in result:
        link = result['link']
    else:
        print("Warning: Link not in db!")
    if 'date' in result:
        date = result['date']
    if 'reddit_url' in result:
        reddit_url = result['reddit_url']
    return Feed(scope=scope,
                title=title,
                desc=desc,
                link=link,
                date=date,
                reddit_url=reddit_url)


def put_reddit_url(url):
    try:
        firebase_db.put(url="/uploadplan", name="reddit_url", data=url)
    except Exception as e:
        print('Error putting reddit url into fb db' + format(e))


def get_reddit_url():
    try:
        result = firebase_db.get("/uploadplan", "reddit_url")
    except Exception as e:
        print('Error getting feed from fb db' + format(e))
        result = None

    return result


def send_fcm(feed, debug=False):
    message = feed.desc
    title = feed.title
    if feed.scope == "uploadplan":
        print(feed.desc)
        # Only send the actual uploadplan
        match = re.search("(?:<p>)?(?:<strong>)?Upload-Plan am.*?(?:</strong>)?(?:<p>|<br ?/?>)(.*?)<\/p>", feed.desc, re.DOTALL)
        if match is not None:
            message = match.group(1)
    elif feed.scope == "video":
        # Only send the title of the video
        title = "Neues Video (pietsmiet.de)"
        message = feed.title
    elif feed.scope == "news":
        # Only send the title of the news item
        title = "News (pietsmiet.de)"
        message = feed.title

    data_message = {
        "title": title,
        "topic": feed.scope,
        "message": message,
        "link": feed.link
    }
    topic = feed.scope
    if debug is True:
        topic = "test"
    try:
        firebase_fcm.notify_topic_subscribers(data_message=data_message, topic_name=topic)
        print("Sent fcm for " + feed.scope + " to topic/" + topic)
    except Exception as e:
        print("Error making new fcm" + format(e))
