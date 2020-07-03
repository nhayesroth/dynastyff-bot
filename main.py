# from urllib.parse import quote_plus

import praw
import pdb
import configparser

from user import User
import utils

def get_top_level_comments(submission):
    submission.comments.replace_more(limit=0)
    return submission.comments

def construct_dict_from_top_level_comments(top_level_comments):
    """Scans the top-level comments and constructs a dictionary mapping(name -> User)."""
    users_by_name = dict()
    for comment in top_level_comments:
        # Ignore comments that have been deleted.
        # TODO: this is bad behavior. better would be to call them out or record the comment before it was deleted.
        if comment.author is None:
            continue
        else:
            username = comment.author.name
            if username in users_by_name.keys():
                user = users_by_name.get(username)
            else:
                user = User(name=username, questions=[])
            user = users_by_name.get(username, User(name=username, questions=[]))
            user.add_question(comment)
            users_by_name[username] = user
            print(f"{username} has asked {len(user.questions)} so far")

    return users_by_name

def scan_replies_to_top_level_comments(users_by_name):
    """Scans replies to top-level comments and updates the users_by_name dict."""
    repliers_by_name = dict()
    for username in users_by_name.keys():
        requestor = users_by_name.get(username)
        questions = requestor.questions
        for question in questions:
            replies = question.replies
            for reply in replies:
                if reply.author is None:
                    # Ignore deleted responses
                    continue
                else:
                    # Update the requestor to track the number of replies they've received
                    requestor.inc_num_replies_to_questions()
                    # Update the replier to track their contributions
                    replier_name = reply.author.name
                    # if (replier_name == "frederferf"):
                    #     pdb.set_trace()
                    replier = repliers_by_name.get(replier_name, User(name=replier_name, questions=[], replies=[]))
                    replier.add_reply(reply)
                    repliers_by_name[replier_name] = replier
                    print(f"{replier_name} has responded {len(replier.replies)} times so far ({utils.get_abbreviated_comment(reply)})")
    # Combine the 2 dictionaries
    for username in repliers_by_name:
        if username in users_by_name:
            requestor = users_by_name.get(username)
            replier = repliers_by_name.get(username)
            combined_user = User.combine(requestor, replier)
            users_by_name[username] = combined_user
    return users_by_name

def get_users_sorted_by_relative_contribution(users_by_name):
    """Returns a list of Users, sorted by their relative contribution (descending)."""
    users = list(users_by_name.values())
    users.sort(key=lambda user: user.relative_contribution(), reverse=True)
    return users

def get_users_sorted_by_replies(users_by_name):
    """Returns a list of Users, sorted by their relative contribution (descending)."""
    users = list(users_by_name.values())
    users.sort(key=lambda user: user.num_replies(), reverse=True)
    return users

def get_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config['GLOBAL']

def get_reddit_instance(config):
    return praw.Reddit(
        user_agent=config['user_agent'],
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        username=config['username'],
        password=config['password'],
    )

def get_submission(reddit_instance, config):
    subreddit = reddit_instance.subreddit(config['subreddit'])
    for submission in subreddit.hot(limit=10):
        if utils.is_target_post(submission, config):
            return submission
    raise ValueError('Unable to find target post. Check the subreddit and post_regex in config.ini')

def print_users(header, users, inline_user_callback, suffix_user_callback=None):
    i = 1
    print(header)
    for user in users:
        user_string = f"{i}. {user.name} - {inline_user_callback(user)}"
        if suffix_user_callback:
            suffix = suffix_user_callback(user)
            for line in suffix:
                user_string += f"\n\t{line}"
        print(user_string)
        i += 1

def main():
    config = get_config();
    reddit_instance = get_reddit_instance(config)
    submission = get_submission(reddit_instance, config)

    top_level_comments = get_top_level_comments(submission)
    users_by_name = construct_dict_from_top_level_comments(top_level_comments)
    users_by_name = scan_replies_to_top_level_comments(users_by_name)
    users_sorted_by_contribution = get_users_sorted_by_relative_contribution(users_by_name)[:10]
    users_sorted_by_replies = get_users_sorted_by_replies(users_by_name)[:10]

    print_users(
        header="Users sorted by contribution",
        users=users_sorted_by_contribution,
        inline_user_callback=User.relative_contribution_summary)

    print_users(
        header="Users sorted by replies",
        users=users_sorted_by_replies,
        inline_user_callback=User.num_replies,
        suffix_user_callback=User.reply_summaries)

    # for user in sorted_users:
    #     print(user)
    # for user in sorted_users:
    #     print(user)


if __name__ == "__main__":
    main()