import praw
from praw.models import Submission
from backend.api_keys import reddit_username, reddit_password, reddit_user_agent, reddit_client_id, reddit_client_secret

subreddit = "pietsmiet"
submission_url = ""

reddit_auth = praw.Reddit(client_id=reddit_client_id,
                     client_secret=reddit_client_secret,
                     password=reddit_password,
                     user_agent=reddit_user_agent,
                     username=reddit_username)


def submit_to_reddit(title, text):
    """
    Posts a link to the given subreddit
    :param title: Title of the reddit post
    :param text: Text to add to the reddit self post
    """

    if (text == '') or (title == ''):
        print("Not submitting to reddit, null text or title")
        return

    # Submit the post
    submission_url = reddit_auth.subreddit(subreddit).submit(title, selftext=text, resubmit=False, send_replies=False).shortlink
    print(submission_url)


def edit_submission(text):
    if (submission_url == ""):
        return
    submission = Submission(reddit_auth, url=submission_url)
    submission.edit(text)
    print("Submission edited")
    
