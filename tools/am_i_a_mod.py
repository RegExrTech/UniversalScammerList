import os
import time
import sys
sys.path.insert(0, ".")
import Config

def get_mod_list():
	return [str(x).lower() for x in sub_config.subreddit_object.moderator()]

subnames = [x.split(".")[0] for x in os.listdir("config/")]
for subname in subnames:
	sub_config = Config.Config(subname)
	try:
		mod_list = get_mod_list()
	except:
		print(subname)
		print("    Unable to get mod list")
		continue
	if sub_config.bot_username.lower() in mod_list:
		continue
	print(subname)
	continue
	title = "YOU MAY LOSE UNIVERSAL SCAMMER LIST ACCESS - PLEASE READ"
	body = "Hello mods of r/" + subname + ".\n\nI am u/" + sub_config.bot_username + " and I am your sub-specific replacement for u/USLbot. I sent you a message a few months ago about how a new system is replacing the old USL system. This migrating is happening within the next 24 hours. If you do not add me as a mod with the following permissions, you **will lose access to the USL**. The required permissions are below:\n\n* Manage Users\n\n* Manage Wiki\n\n* Manage Mod Mail\n\nThe message you were last sent has been copied before for your convenience. Please reach out to the mods of r/UniversalScammerList via Mod Mail if you have any question.\n\n---\n\nAs you might have heard, u/RegExr has been collaborating with u/Tjstretchalot to work on a replacement for the USL system. The replacement places an emphasis on scalability so USL actions will be faster and can easily handle more communities. Part of this change requires each sub to have their own USL bot rather than one bot instance shared across all communities. Please add u/" + sub_config.bot_username +  " as a moderator to your community with the following permissions:\n\n* Manage Users\n\n* Manage Mod Mail\n\n* Manage Wiki Pages\n\nOf course, you're welcome to give more permissions than that, but that is the minimum needed for the bot to work properly. This is two more permissions than previously needed but they enable the following features:\n\n* Updates sent via Mod Mail\n\n  * Projects worked on by u/RegExr often see regular updates. If changes and new features need to be communicated to your community, an automated message will be sent via Mod Mail. By giving the bot account Mod Mail permissions, the messages can be sent as Mod Discussion, making them easier to find and read.\n\n* Mod-Managed Configuration\n\n  * Each subreddit will have its own mod-only wiki page where you can manage the configuration for your USL bot. Currently, the only configuration you can manage is which tags you are subscribed to, but more configurations will be coming soon (and announced via Mod Mail). Once the bot is running on your subreddit, the configuration page can be found [here](https://www.reddit.com/r/" + subname + "/wiki/usl_config/).\n\nPlease feel free to reach out to u/RegExr or to the USL mod group via [Mod Mail](https://www.reddit.com/message/compose?to=%2Fr%2FUniversalScammerList) if you have any questions. Thank you for your help in getting this off the ground! We're excited to enter this new phase of the USL.\n\nBest,\n\nu/" + sub_config.bot_username + " and u/RegExr"
	try:
		sub_config.subreddit_object.message(title, body)
	except Exception as e:
		print("Unable to send message to " + subname + " with error " + str(e))
