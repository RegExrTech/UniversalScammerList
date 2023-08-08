import os
import time
import sys
sys.path.insert(0, ".")
import Config

f_path = 'database/mods.txt'

if not os.path.exists(f_path):
	os.mknod(f_path)

f = open(f_path, 'r')
already_sent = set(f.read().splitlines())
f.close()

title = "[PLEASE READ] Universal Scammer List Usage Guide"

subnames = [x.split(".")[0] for x in os.listdir("config/")]
for subname in subnames:
	if subname == 'funkoppopmod':
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
		try:
			mod.message(subject=title, message=body)
		except Exception as e:
			print("  Unable to send message to u/" + mod_name + " on sub r/" + subname + " with error " + str(e))
			time.sleep(60)
		print("Found a new mod! User is u/" + mod_name)
		time.sleep(20)
		already_sent.add(mod_name)

f = open(f_path, 'w')
already_sent = list(already_sent)
already_sent.sort()
f.write("\n".join(already_sent))
f.close()
