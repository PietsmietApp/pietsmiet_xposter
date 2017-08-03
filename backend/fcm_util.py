import time
import re

from pyfcm import FCMNotification
import pyfcm

from backend.api_keys import fcm_key
from backend.log_util import log

firebase_fcm = FCMNotification(api_key=fcm_key)


def send_fcm(feed, debug=False):
    global firebase_fcm
    message = feed.desc
    title = feed.title
    # game = None
    if feed.scope == "uploadplan":
        message = get_uploadplan_from_desc(feed.desc)
    elif feed.scope == "video":
        # Only send the title of the video (as message)
        title = "Neues Video (pietsmiet.de)"
        message = feed.title
        # game = get_game_from_video(message)
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
        # "game": game
    }
    topic = feed.scope
    low_priority = True
    if debug is True:
        topic = "test_neu"
        low_priority = False

    retry_count = 1

    while retry_count <= 3:
        log("Info", "Sending fcm for " + feed.scope + " to topic/" + topic +
            " with content: " + message)
        try:
            firebase_fcm.notify_topic_subscribers(data_message=data_message,
                                                  topic_name=topic,
                                                  time_to_live=86400,
                                                  low_priority=low_priority)
            return True
        except pyfcm.errors.FCMServerError as e:
            retry_time = pow(4, retry_count)
            log("Warning", "Firebase servers are asleep, new try in " + str(retry_time) + " seconds." +
                "\n Exception is: " + format(e))
            time.sleep(retry_time)
            firebase_fcm = FCMNotification(api_key=fcm_key)
            retry_count += 1
    return False


def get_uploadplan_from_desc(desc):
    # Only send the actual uploadplan
    match = re.search(
        "(?:<p>)?(?:<strong>)?Upload-Plan am \d\d?\..*?(?:</strong>)?(?:<p>|<br ?/?>)(.{120,}?)(?:<br ?/?>)*<\/p>",
        desc,
        re.DOTALL)
    if match is not None:
        return match.group(1)
    else:
        log("Error", "No Uploadplan found in desc! Uploadplan was:\n " + desc)
        return "In der App ansehen..."


def get_game_from_video(message):
    if (u'\U0001f3ae' in message) or ('|' in message):
        # Check which game this is
        match = re.search("(?:\U0001F3AE|\|) ?(.*)", message)
        if match is not None:
            complete_game = match.group(1)
            # Strip hashtag from game and remove unicode chars
            game = re.sub(r" ?# ?\d+ ?", "", complete_game).encode('unicode_escape').decode('latin-1', 'ignore')
            # Verify that the game name length is longer than 2 chars
            if len(str(game)) > 2:
                return game
    else:
        return "Vlog"

    return None
