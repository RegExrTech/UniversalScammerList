import os
import time
import sys
sys.path.insert(0, ".")
import Config

# These mods don't count for representation
blacklist_mod_names = ['automoderator']

def main():
	unrepresented_subs = []

	subnames = [x.split(".")[0] for x in os.listdir("config/")]
	usl_sub_config = Config.Config('logger')
	try:
		usl_sub_mods = usl_sub_config.subreddit_object.moderator()
	except:
		print("    Unable to get mod list from r/" + subname + " which is fatal.")
		return
	usl_sub_mods = set([x.name.lower() for x in usl_sub_mods])


	for subname in subnames:
		if subname in ['funkoppopmod', 'universalscammerlist', 'forhire']:
			continue
		sub_config = Config.Config(subname)
		try:
			mod_list = sub_config.subreddit_object.moderator()
		except:
			print("    Unable to get mod list from r/" + subname)
			continue
		# Wait until the bot is a mod of the sub to send messages
		if sub_config.bot_username.lower() not in [x.name.lower() for x in mod_list]:
			continue

		# Only subs with write access need to be represented
		if not sub_config.write_to:
			continue

		if not any([x.name.lower() in usl_sub_mods for x in mod_list if not x.name.lower() in blacklist_mod_names]):
			unrepresented_subs.append(subname)

			title = "[PLEASE READ] r/" + subname + " is not represented in r/UniversalScammerList"

			offender_body = "Hello, mods of r/" + subname + ". Your subreddit is a participating subreddit of the Universal Scammer List. However, none of your mods are moderators in r/UniversalScammerList. The USL requires that at least one **ACTIVE** moderator from your sub also be a moderator of r/UniversalScammerList. This ensures that your sub is properly represented and issues regarding your sub can be dealt with swiftly.\n\n"
			offender_body += "Please nominate one of your moderators to join r/UniversalScammerList and send your selection as a mod mail message to r/UniversalScammerList. Once you've done so, that user will be invited as a mod shortly. If you do **not** choose a mod to represent your sub, you could lose access to the USL.\n\n"
			offender_body += "Thank you for your help. Please reach out to the mod team of r/UniversalScammerList if you have any questions!"
			try:
				usl_sub_config.reddit.subreddit(sub_config.subreddit_name).message(subject=title, message=offender_body)
			except Exception as e:
				print("Unable to send message to r/" + sub_config.subreddit_name + " with error " + str(e))
			time.sleep(30)

	# If there are no unrepresented subs, break out early
	if not unrepresented_subs:
		return

	title = "The following subs are not represented in r/UniversalScammerList"
	usl_sub_body = "Hello, mods of r/UniversalScammerList. During a routine inspection, I noticed that none of the mods from the follow subs are  represented on r/UniversalScammerList:\n\n"
	usl_sub_body += "* r/" + "\n\n* r/".join(unrepresented_subs) + "\n\n"
	usl_sub_body += "I've sent a message to the above subs informing them that they should nominate one of their active mods to represent their sub on r/UniversalScammerList and that failure to do so may result in their sub losing USL access.\n\n"
	usl_sub_body += "This message is informational and no action is required at this time. However, if the subs fails to nominate moderators to represent their sub, a discussion should be had about their sub having access to the USL.\n\n"
	usl_sub_body += "Thank you for your help and participation!"
	try:
		Config.Config('funkoppopmod').reddit.subreddit('universalscammerlist').message(subject=title, message=usl_sub_body)
	except Exception as e:
		print("Unable to send message to r/UniversalScammerList with error " + str(e))



if __name__ == "__main__":
	main()
