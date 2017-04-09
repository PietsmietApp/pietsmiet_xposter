from backend.api_keys import uploadplan_url, news_url, video_url

SCOPE_UPLOADPLAN = "uploadplan"
SCOPE_PIETCAST = "pietcast"
SCOPE_NEWS = "news"
SCOPE_VIDEO = "video"


def get_url_for_scope(scope):
    if scope == SCOPE_UPLOADPLAN:
        return uploadplan_url
    elif scope == SCOPE_PIETCAST:
        return "http://www.pietsmiet.de/pietcast/feed/podcast/"
    elif scope == SCOPE_NEWS:
        return news_url
    elif scope == SCOPE_VIDEO:
        return video_url
