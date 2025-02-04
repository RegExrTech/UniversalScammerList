import os
import random
import string
import time
import sys
sys.path.insert(0, ".")
import Config

def main():
	usl_config = Config.Config('logger')
	usl_mods = [x.name for x in usl_config.subreddit_object.moderator()]

	already_sent = set([])
	subnames = [x.split(".")[0] for x in os.listdir("config/")]

	title = "[Poll] Vote on USL-Representation Policies and Voting Practices"
	body = "Hi folks,\n\nThere's been a lot of discussion over the last year or so about how much say any individual moderator and community should have over the USL. The following poll has gone through a few rounds of feedback and is ready for your opinion. Please click the link below and select answers for the following five questions.\n\nhttps://docs.google.com/forms/d/e/1FAIpQLSfGwKOpGhKbyzraKHwmlhrSZ58JFY9b0Y1NeSee4Ftdp7zfwg/viewform?usp=sf_link"

	for subname in subnames:
		if subname == 'logger':
			continue
		sub_config = Config.Config(subname)
		print("=== " + subname + " ===")
		config_page_string = "[config page](https://www.reddit.com/r/" + sub_config.subreddit_name + "/wiki/usl_config/)"
		if subname == 'funkoppopmod':
			continue
		try:
			mod_list = sub_config.subreddit_object.moderator()
		except:
			print("    Unable to get mod list")
			continue
		if sub_config.bot_username.lower() not in [x.name.lower() for x in mod_list]:
			print("    I am not a mod")
			continue
#		title = "[USL Bot Update] USL Bots now auto-claim subreddits based on their names"
#		body = "Hey folks!\n\nAs you may or may not know, scams have been on the rise where a scammer will claim a subreddit based on a moderator's name (e.g. r/RegExr) and send mod mail messages *as the subreddit* to impersonate moderators. This is a very successful scam method and can only be stopped by beating would-be scammers to the punch and claiming your subreddit ahead of them OR by messaging the admins to get control of the sub if they beat you to it.\n\nIn an effort to prevent this from happening, I've gone ahead and had each USL bot create a subreddit based on their name. The subreddit is private so you won't see it if you click on the bot's profile, but you can find it by directly navigating to it. All existing bots have had their subs claimed and all new bots will automatically claim their subs as a part of their initialization process.\n\nThis is mostly just a heads up message in case you come across the aforementioned subreddits and have any questions or concerns. However, this is also a good time to remind folks to claim their subreddits before someone else does.\n\nThanks for reading this message and please let u/RegExr know if you have any questions!\n\nBest,\n\nu/RegExr"
		send_to_usl_mods(mod_list, usl_mods, already_sent, 'UniversalScammerList', title, body)
#		send_mod_discussion(sub_config, title, body)

def send_to_all_mods(mod_list, already_sent, subname, title, body):
	for mod in mod_list:
		if mod.name in already_sent:
			continue
		if 'uslbot' in mod.name.lower() or 'automod' in mod.name.lower():
			continue
		if 'bot' == mod.name.lower()[-3:]:
			print("Skipping bot account u/" + mod.name + " on sub r/" + subname)
			continue
		unique_id = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=6))
		footer = "\n\n---\n\nYour unique ID is " + unique_id + ". Please use this code when filling out the above survey or else your response will not be counted. Do not share this code with anyone as it is unique to you."
		try:
			mod.message(subject=title, message=body + footer)
		except Exception as e:
			print("Unable to send message to u/" + mod.name + " on sub r/" + subname + " with error " + str(e))
			time.sleep(60)
		time.sleep(20)
		already_sent.add(mod.name)
		print("[" + unique_id + "] Sent to u/" + mod.name)

def send_to_usl_mods(mod_list, usl_mods, already_sent, subname, title, body):
	mod_list = [x for x in mod_list if x.name in usl_mods]
	send_to_all_mods(mod_list, already_sent, subname, title, body)

def send_mod_discussion(sub_config, title, body):
	try:
		sub_config.subreddit_object.message(subject=title, message=body)
	except Exception as e:
		print("Unable to send message to " + subname + " with error " + str(e))

def send_to_usl_reps():
	already_sent = set()
	title = "USL Downtime For Database Migration"
	subnames = [x.split(".")[0] for x in os.listdir("config/")]
	for subname in subnames:
		if subname == 'logger':
			continue
		sub_config = Config.Config(subname)
		if not sub_config.usl_rep:
			continue
		rep = sub_config.reddit.redditor(sub_config.usl_rep)
		if rep.name in already_sent:
			continue
		already_sent.add(rep.name)
		body = "Hello u/" + rep.name + ",\n\nYou are receiving this message because you are listed as the USL rep of r/" + subname + ". I'm writing to let you know that the USL service is currently down while I perform a database migration. Once complete, this migration will allow the USL website to return results instantly rather than forcing users to wait a long time for the database to load. \n\nWhile the USL service is down, new bans and unbans will not be reflected in the USL. However, once service resumes, the bot will catch up on all actions, so please continue to operate as if the USL was still running. Also, note that this does NOT impact the USL website. The site is still up and operational, but will just not reflect any new bans or unbans. \n\nI anticipate this migration taking a few hours, so please be patient as this runs. I will send another update once the USL is back up and running.\n\nPlease pass this information along to your moderation team if they have any questions about the USL's current status. \n\nThanks for your help! Looking forward to this new change going live.\n\nBest,\n\nu/RegExr"
		try:
			rep.message(subject=title, message=body)
		except Exception as e:
			print("Unable to message u/" + rep.name + " with error " + str(e))

#main()
send_to_usl_reps()
