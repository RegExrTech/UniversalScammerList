import os
import time
import sys
sys.path.insert(0, ".")
import Config
import discord

f_path = 'database/usl_mods.txt'

if not os.path.exists(f_path):
	os.mknod(f_path)

f = open(f_path, 'r')
already_sent = set(f.read().splitlines())
f.close()

title = "[PLEASE READ] How To Be a Mod of r/UniversalScammerList"

def main():
	sub_config = Config.Config('logger')
	try:
		mod_list = sub_config.subreddit_object.moderator()
	except:
		print("    Unable to get mod list from r/UniversalScammerList when running usl_mod_onboarder.py")
		return

	body = "Hi there! If you're receiving this message, it means that either you have joined as a moderator of r/UniversalScammerList. This means you are the USL representative of your subreddit. As such, there are a few things to know. Please read this entire message as it contains important information.\n\n"
	body += "* Your main responsibility as a USL rep is to be the point of contact for any ban disputes that arise from your sub. For example, if a user comes to us contesting a ban from your sub, it is your responsibility to provide context and justification for the ban and engage in discussion. It's possible that the ban was applied incorrectly, so it's important to come to these discussions with an open mind! There are a lot of people involved with the USL with a lot of different backgrounds and experiences, so it's important to focus on good communication and collaboration rather than strong defenses of our current positions.\n\n"
	body += "* As a USL mod, you are also expected to participate in discussions via modmail. Again, as a representative of your sub, it's important to offer your opinion on how the USL operates. The USL covers a lot of ground, so making sure every sub is heard and the system works as best it can for all participants is one of the main goals of the USL. By voicing your opinions, you're helping to make the USL the best it can be through growth and change.\n\n"
	body += "* Occasionally, when changes to the USL are proposed, polls to USL representatives are sent out via DMs from the USL bot. Please respond to these polls within 72 hours.\n"
	body += "    * Results from USL mod polls can be found [here](https://www.universalscammerlist.com/voting).\n\n"
	body += "* Please check USL modmail with some level of frequency. A handy link for viewing just USL modmail messages can be found [here](https://mod.reddit.com/mail/search?q=%20subreddit%3AUniversalScammerList). Consider bookmarking this link for easy access.\n"
	body += "    * Modmail is generally low effort, but occasionally generates a lot of messages in a short amount of time due to the number of people participating in conversations. If you have modmail notifications enabled through the official reddit mobile app and the number of notifications you get bothers you, please consider disabling modmail notifications within the app settings.\n"
	body += "    * If you do not wish to see USL modmail messages in your general modmail inbox view, please consider unselecting r/UniversalScammerList from the list of subreddits you moderate within modmail in the left side bar. This will prevent USL modmail messages from appearing. When you want to catch up on USL modmail messages, simply reselect the sub and the messages will reappear.\n"
	body += "    * Please avoid archiving modmail messages before they are resolved. Archiving a modmail message archives it for everyone, not just you. Please see [this USL page](https://www.universalscammerlist.com/voting) for more information.\n\n"
	for mod in mod_list:
		mod_name = mod.name.lower()
		if mod_name in already_sent:
			continue
		try:
			mod.message(subject=title, message=body)
		except Exception as e:
			discord.log("  Unable to send message to u/" + mod_name + " on sub r/UniversalScammerList with error " + str(e))
			time.sleep(60)
		discord.log("u/" + mod_name + " has joined as a USL mod.")
		already_sent.add(mod_name)
		# Do this every time we find a new mod, rather than at the end, so overlapping scripts don't send the same message twice.
		f = open(f_path, 'w')
		to_write = list(already_sent)
		to_write.sort()
		f.write("\n".join(to_write))
		f.close()

if __name__ == '__main__':
	main()
