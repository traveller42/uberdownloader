import urllib2
import time
import json
import sys
import os
import os.path
import traceback

def get_page_with_wait(url, wait=6):  # SGF throttling is 10/minute
    global request_successful
    global max_retries
    global current_retry

    if wait < 0.01:
        wait = 0.01

    print(time.time(), wait, current_retry)

    try:
        time.sleep(wait)
        response = urllib2.urlopen(url)
    except urllib2.HTTPError as e:
        if e.code == 429:  # too many requests
            print("Too many requests / minute, falling back to {} seconds between fetches.".format(int(1.5 * wait)))
            # exponential falloff
            return get_page_with_wait(url, wait=(1.5 * wait))
        raise
    except urllib2.URLError as e:
        if e.reason.errno == -2:  # Name or service not known
            if request_successful:
                if current_retry < max_retries:
                    print("Address lookup error after success.  Trying again.")
                    current_retry += 1
                    return get_page_with_wait(url, 5)  # Wait 5 seconds between retries
            print("Address lookup failing.  Check your network connection")
            exit(1)
        raise
    else:
        # everything is fine
        current_retry = 0
        request_successful = True
        return response.read()

def results(url):
    while url is not None:
        data = json.loads(get_page_with_wait(url, 0))
        for r in data["results"]:
            yield r
        url = data["next"]

def user_games(user_id):
    url = "https://online-go.com/api/v1/players/{}/games/?format=json".format(user_id)
    for r in results(url):
        yield r["id"]

def user_reviews(user_id):
    return
    url = "https://online-go.com/api/v1/reviews/?owner__id={}&format=json".format(user_id)
    for r in results(url):
        yield r["id"], r["game"]["id"]

def reviews_for_game(game_id):
    return
    url = "https://online-go.com/api/v1/games/{}/reviews?format=json".format(game_id)
    for r in results(url):
        yield r["id"]

def save_sgf(out_filename, SGF_URL, name):
    if os.path.exists(out_filename):
        print("Skipping {} because it has already been downloaded.".format(name))
    else:
        print("Downloading {}...".format(name))
        sgf = get_page_with_wait(SGF_URL)
        with open(out_filename, "w") as f:
            f.write(sgf)

if __name__ == "__main__":
    user_id = int(sys.argv[1])
    dest_dir = sys.argv[2]

    request_successful = False
    max_retries = 5
    current_retry = 0

    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)

    for g in user_games(sys.argv[1]):
        save_sgf(os.path.join(dest_dir, "OGS_game_{}.sgf".format(g)),
                 "https://online-go.com/api/v1/games/{}/sgf".format(g),
                 "game {}".format(g))
        for r in reviews_for_game(g):
            save_sgf(os.path.join(dest_dir, "OGS_game_{}_review_{}.sgf".format(g, r)),
                     "https://online-go.com/api/v1/reviews/{}/sgf".format(g),
                     "review {} of game {}".format(r, g))

    for r, g in user_reviews(sys.argv[1]):
            save_sgf(os.path.join(dest_dir, "OGS_game_{}_review_{}.sgf".format(g, r)),
                     "https://online-go.com/api/v1/reviews/{}/sgf".format(g),
                     "review {} of game {}".format(r, g))

