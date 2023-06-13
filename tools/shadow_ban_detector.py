import praw
import sys
sys.path.insert(0, '.')
import Config
import os

sub_config = Config.Config('funkoppopmod')
reddit = sub_config.reddit

subnames = [x.split(".")[0] for x in os.listdir("config/")]
for subname in subnames:
	sub_config = Config.Config(subname)
	try:
		bot = reddit.redditor(sub_config.bot_username)
		m = bot.is_mod
	except Exception as e:
		print(sub_config.bot_username + " is shadowbanned.")
