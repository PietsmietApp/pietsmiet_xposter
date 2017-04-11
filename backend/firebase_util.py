from backend.api_keys import fcm_key, fb_db_key
from backend.rss_util import Feed
from pyfcm import FCMNotification
from firebase import firebase
import re

firebase_fcm = FCMNotification(api_key=fcm_key)
firebase_db = firebase.FirebaseApplication('https://pietsmiet-de5ff.firebaseio.com/', authentication=fb_db_key)


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
        
    if (result is None):
        return Feed(scope=scope, title='none_title')
    else:
        reddit_url = None
        if 'reddit_url' in result:
            reddit_url = result['reddit_url']
        return Feed(scope=scope, 
            title=result['title'], 
            desc=result['desc'], 
            link=result['link'], 
            date=result['date'],
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
    

def send_fcm(feed):
    message = feed.desc
    title = feed.title
    if feed.scope == "uploadplan":
        #Only send the actual uploadplan
        match = re.search("<strong>Upload.*?< ?br ?\/? ?>(.*?)<\/p>", feed.desc)
        if match != None:
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
        "title" : title,
        "topic" : feed.scope,
		"message" : message,
        "link" : feed.link
    }
    try:
        firebase_fcm.notify_topic_subscribers(data_message=data_message, topic_name=feed.scope)
        print("Sent fcm for " + feed.scope)
    except Exception as e:
        print("Error making new fcm" + format(e))
