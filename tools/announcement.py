import os
import time
import sys
sys.path.insert(0, ".")
import Config

already_sent = set([])

subnames = [x.split(".")[0] for x in os.listdir("config/")]
for subname in subnames:
	sub_config = Config.Config(subname)
	print(subname)
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
	title = "[PLEASE READ] New USL Feature - Ban Tag Typo Checking"
	body = "Hello Mod Team!\n\nI am writing to you today to let you know that a new feature has been launched as a part of the USL.\n\nWhen going through the old USL data prior to the migration, I noticed the following different ways sketchy had been spelled over the years\n\n* kstechy\n\n* skeychy\n\n* skechy\n\n* sketcky\n\n* skektchy\n\n* skethcy\n\n* sketch\n\n* sktechy\n\n* sletchy\n\nThese are all obviously typos and resulted in these users not being properly banned on the USL like they should have been.\n\nNow, with typo checking, if a ban is issued and there are tags present in the mod note, the bot will check those tags against the set of known tags. If typo checking is enabled, the bot will send a message to the moderator who issued the ban ((example)[https://imgur.com/a/ILhCkw9]), letting them know which tags were unrecognized in the mod note. This gives that moderator a chance to reissue the ban and ensure the users is properly sent to the USL.\n\nThis feature is set to OFF by default. This is because some subreddits use USL-like tags in their mod notes for unrelated reasons. Those subs will likely not want to enable this feature as it'll send them a message every time they use a non-USL tag in a mod note. But if your sub does NOT use tags for anything other than the USL, I would **strongly suggest that you enable this feature ASAP**. This feature can be enabled by navigating to your [config page](https://www.reddit.com/r/" + sub_config.subreddit_name + "/wiki/usl_config/) and editing the value of `typo_checking` from `False` to `True`. Once you do so, the USL bot will start checking for typos in your mod notes going forward\n\nPlease reach out to u/RegExr directly if you have any questions about this! More information can be seen at the bottom of the [How To](https://www.universalscammerlist.com/about.html) page of the USL site.\n\nThanks for reading! Happy banning!\n\nBest,\n\nu/RegExr"
	try:
		sub_config.subreddit_object.message(subject=title, message=body)
	except Exception as e:
		print("Unable to send message to " + subname + " with error " + str(e))
		continue

#	id = [x.id for x in  sub_config.subreddit_object.modmail.conversations(state='mod', limit=1)][0]
#
#	title = "[PLEASE READ] New USL System Officially Launched!"
#	for mod in mod_list:
#		if mod.name in already_sent:
#			continue
#		if 'uslbot' in mod.name.lower() or 'automod' in mod.name.lower():
#			continue
#		if 'bot' == mod.name.lower()[-3:]:
#			print("Skipping bot account u/" + mod.name + " on sub r/" + subname)
#			continue
#		body = "Hello u/" + mod.name + ",\n\nYou are receiving this message because you are a moderator of r/" + subname + ". A major update has just been released for the automated Universal Scammer List System. Please **READ THIS MOD DISCUSSION POST** for more information: https://mod.reddit.com/mail/mod/" + id + "\n\nThank you for your help in migrating to this new system! Please let me know if you have any questions.\n\nBest,\n\nu/RegExr"
#		try:
#			mod.message(title, body)
#		except Exception as e:
#			print("Unable to send message to u/" + mod.name + " on sub r/" + subname + " with error " + str(e))
#			time.sleep(60)
#		time.sleep(20)
#		already_sent.add(mod.name)
