import requests
import os
import time
import sys
sys.path.insert(0, ".")
import Config
import discord
import tags

# THIS SCRIPT ONLY NEEDS TO CHECK IF *NEW* MODS ARE ON THE USL
# When an existing mod is added to the USL, the main usl.py script handles notifying
# So all this is doing is check if newly added USL mods are already on the USL or not

request_url = "http://0.0.0.0:8080"
f_path = 'database/all_mods.txt'

if not os.path.exists(f_path):
	os.mknod(f_path)

f = open(f_path, 'r')
already_sent = set(f.read().splitlines())
f.close()

title = "USL-banned user has been added as a mod of r/"

subnames = [x.split(".")[0] for x in os.listdir("config/")]
for subname in subnames:
	if subname == 'funkoppopmod':
		continue
	sub_config = Config.Config(subname)
	try:
		mod_list = sub_config.subreddit_object.moderator()
	except:
		continue
	# Wait until the bot is a mod of the sub to send messages
	if sub_config.bot_username.lower() not in [x.name.lower() for x in mod_list]:
		continue
	body = "Hi there! If you're receiving this message, it means that either you have joined r/" + subname + " as a new moderator or r/" + subname + " has just started participating in the Universal Scammer List.\n\n"
	body += "If you're new to using the Universal Scammer List as a moderator, please review the [usage guide](https://www.universalscammerlist.com/about) as soon as possible. It gives details on how to configure the bot, how to add and remove bans from the USL, and more.\n\n"
	body += "If you have any questions, please reach out to the mod group on r/UniversalScammerList or feel free to message u/RegExr directly.\n\n"
	body += "Thank you so much for your help and participation!"
	for mod in mod_list:
		mod_name = mod.name.lower()
		if mod_name in already_sent:
			continue
		if 'uslbot' in mod_name or 'automod' in mod_name:
			continue
		if 'bot' == mod_name[-3:]:
			continue
		ban_data = requests.get(request_url + "/get-ban-data/", data={'banned_user': mod_name}).json()

		should_notify = True
		if not ban_data:
			should_notify = False
		elif not any([x in tags.PUBLIC_TAGS for x in ban_data.keys()]):
			should_notify = False

		if should_notify:
			message_content = "Hello, mods of r/" + sub_config.subreddit_name + ". Recently, u/" + mod_name + " was added as a mod of your sub. However, this user is [listed on the UniversalScammerList](https://www.universalscammerlist.com/?username=" + mod_name + "). The USL does not allow membership to subreddits with mods who are on the list, so please remedy this situation either by removing the offending mod from the mod team or by reaching out to the r/UniversalScammerList mod mail to resolve the issue.\n\nThanks for your cooperation!"
			sub_config.subreddit_object.message(subject=title + sub_config.subreddit_name, message=message_content)
			message_content = "Hello, USL Mods. Recently, u/" + mod_name + " was added as a moderator of r/" + sub_config.subreddit_name + ". However, this user is [listed on the UniversalScammerList](https://www.universalscammerlist.com/?username=" + mod_name + "). I have notified the offending subreddit. Please discuss if the subreddit in question should retain USL access.\n\nThanks!"
			sub_config.reddit.subreddit('universalscammerlist').message(subject=title + sub_config.subreddit_name, message=message_content)
			discord.log("User u/" + mod_name + " has joined r/" + subname + " as a mod but is on the [UniversalScammerList](https://www.universalscammerlist.com/?username=" + mod_name + ")")

		already_sent.add(mod_name)
		# Do this every time we find a new mod, rather than at the end, so overlapping scripts don't send the same message twice.
		f = open(f_path, 'w')
		already_sent = list(already_sent)
		already_sent.sort()
		f.write("\n".join(already_sent))
		f.close()
		already_sent = set(already_sent)
