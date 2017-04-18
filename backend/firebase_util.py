import re

from firebase import firebase
from pyfcm import FCMNotification

from backend.api_keys import fcm_key, fb_db_key, fb_db_url
from backend.rss_util import Feed

firebase_fcm = FCMNotification(api_key=fcm_key)
firebase_db = firebase.FirebaseApplication(fb_db_url, authentication=fb_db_key)


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
            "date": feed.date
        }
        firebase_db.put(url="/new/" + scope, name=name, data=data)
    except Exception as e:
        print('Error putting feed into fb db' + format(e))


def get_last_feeds(scope):
    try:
        result = firebase_db.get("/new/" + scope, None, params={'orderBy': '"pubDate"', 'limitToLast': '3'})
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
        else:
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


def update_desc(new_feed):
    name = get_id_of_feed(new_feed)
    try:
        result = firebase_db.put("/new/uploadplan/" + name, "desc", data=new_feed.desc)
    except Exception as e:
        print('Error updating feed desc: ' + format(e))
        result = None

    return result


def get_reddit_url():
    try:
        result = firebase_db.get("/new/uploadplan", None, params={'orderBy': '"pubDate"', 'limitToLast': '1'})
        if 'reddit_url' in result[0]:
            return result[0]['reddit_url']
        else:
            print("No reddit url in result")
    except Exception as e:
        print('Error getting reddit url feed from fb db' + format(e))

    return None


def send_fcm(feed, debug=False):
    message = feed.desc
    title = feed.title
    if feed.scope == "uploadplan":
        print(feed.desc)
        # Only send the actual uploadplan
        match = re.search("(?:<p>)?(?:<strong>)?Upload-Plan am.*?(?:</strong>)?(?:<p>|<br ?/?>)(.*?)</p>", feed.desc,
                          re.DOTALL)
        if match is not None:
            message = match.group(1)
    elif feed.scope == "video":
        # Only send the title of the video (as message)
        title = "Neues Video (pietsmiet.de)"
        message = feed.title
    elif feed.scope == "news":
        # Only send the title of the news item (as message)
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


def get_id_of_feed(feed):
    title = re.sub(r'[^a-zA-Z0-9]+', '', feed.title)
    return title + str(feed.date)
