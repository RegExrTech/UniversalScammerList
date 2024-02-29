import requests
import argparse
import time
import os
import random
import sys
sys.path.insert(0, '.')
import Config
import usl

parser = argparse.ArgumentParser()
parser.add_argument('subreddit_name', metavar='C', type=str)
args = parser.parse_args()
subreddit_name = args.subreddit_name.lower()

def main():
	while True:
		config = Config.Config(subreddit_name)
		# If the sub has lost read and write access, stop running.
		if not config.read_from and not config.write_to:
			requests.post(usl.request_url + "/remove-sub-from-action-queue/", {'sub_name': subreddit_name})
			print("r/" + subreddit_name + " has usl all USL access and has been removed from the action queue.")
			return
		os.system('python3 usl.py ' + subreddit_name)
		time.sleep(random.randint(30, 60))

main()
