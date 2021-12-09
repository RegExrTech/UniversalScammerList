import praw
import os
import json

def ascii_encode_dict(data):
        ascii_encode = lambda x: x.encode('ascii') if isinstance(x, unicode) else x
        return dict(map(ascii_encode, pair) for pair in data.items())

def get_json_data(fname):
        with open(fname) as json_data:
                data = json.load(json_data, object_hook=ascii_encode_dict)
        return data

class Config():

	def __init__(self, sub_name):
		config = get_json_data("config/" + sub_name + ".json")

		self.subreddit_name = config['subreddit_name'].lower()
		self.client_id = config['client_id']
		self.client_secret = config['client_secret']
		self.bot_username = config['bot_username']
		self.bot_password = config['bot_password']
		# If this account has permission to write bans to the USL
		self.write_to = config['write_to']
		# If this account has permission to read bans from the USL
		self.read_from = config['read_from']
		# Tags that this account is subscribed to
		self.tags = config['tags']
		self.reddit = praw.Reddit(client_id=self.client_id, client_secret=self.client_secret, user_agent='USL Bot for ' + self.subreddit_name + ' v1.0 (by u/RegExr)', username=self.bot_username, password=self.bot_password)
		self.subreddit_object = self.reddit.subreddit(self.subreddit_name)


	def is_bot_name(self, bot_name):
		# TODO uncomment that bit below
		return bot_name.lower() == self.bot_username.lower() # or bot_name.lower() == "uslbot"
