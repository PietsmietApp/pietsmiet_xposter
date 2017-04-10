from backend.rss_util import Feed
import sqlite3
conn = sqlite3.connect('pietsmiet.db')
c = conn.cursor()


# CREATE TABLE feeds (scope TEXT PRIMARY KEY, title TEXT, desc TEXT, link TEXT, reddit_url TEXT)

def write_feed(feed):
    c.execute("INSERT OR REPLACE INTO feeds(scope,title, desc, link) VALUES" 
            + "('" + feed.scope + "', '"
            + feed.title + "', '"
            + feed.desc + "', '" 
            + feed.link + "')") 
    conn.commit()
    
    
def get_last_feed(scope):
    c.execute("SELECT * FROM feeds WHERE scope='" + scope + "'")
    data = c.fetchone()
    if(data is not None):
        return Feed(title=data[1], link=data[3], date=None, desc=data[2], scope=data[0])     
    else:
        return None
    
    
def get_reddit_url():
    c.execute("SELECT reddit_url FROM feeds WHERE scope = 'uploadplan'")
    data = c.fetchone()
    if(data is not None) and (data[0] is not None) and (data[0] != ''):
        return data[0]
    else:
        return None
    
    
def insert_reddit_url(url):
    c.execute('UPDATE feeds SET reddit_url = "' + url + '" WHERE scope="uploadplan"')
    conn.commit()
