import praw
from praw.models import Submission
from backend.api_keys import reddit_username, reddit_password, reddit_user_agent, reddit_client_id, reddit_client_secret
from backend.log_util import log

reddit_auth = praw.Reddit(client_id=reddit_client_id,
                          client_secret=reddit_client_secret,
                          password=reddit_password,
                          user_agent=reddit_user_agent,
                          username=reddit_username)


def submit_to_reddit(title, text, debug=False):
    """
    Posts a link to the given subreddit
    :param debug: Submit to test subreddit if ture
    :param title: Title of the reddit post
    :param text: Text to add to the reddit self post
    """
    if debug is True:
        subreddit = "l3d00m"
    else:
        subreddit = "pietsmiet"

    if (text == '') or (title == ''):
        log("Warning: Not submitting to reddit, null text or title")
        return

    # Submit the post
    submission_url = reddit_auth.subreddit(subreddit).submit(title, selftext=text, resubmit=False,
                                                             send_replies=False).shortlink
    log("Debug", submission_url)
    return submission_url


def edit_submission(text, submission_url):
    if submission_url == "":
        log("EDIT: Submission url is empty")
        return
    submission = Submission(reddit_auth, url=submission_url)
    submission.edit(text)
    log("Submission edited")


def delete_submission(submission_url):
    if submission_url == "":
        log("Warning", "DELETE: Submission url is empty")
        return
    submission = Submission(reddit_auth, url=submission_url)
    # Only remove the submission if there are less than 4 comments, otherwise unsticky
    comment_count = len(submission.comments.list())
    if comment_count < 5:
        submission.mod.remove()
        submission.mod.lock()
        log("Submission removed")
    else:
        submission.mod.sticky(False)
        log("Submission unstickied")
