import sys
sys.path.insert(0, ".")
import discord
from Config import Config
import wiki_helper
import os

WIKI_PAGE_NAME = "participating_subreddits"
log_bot = Config('logger')
write_names = []
read_names = []

for fname in os.listdir("config"):
	config = Config(fname.split(".")[0])
	if config.write_to:
		write_names.append("r/" + config.subreddit_name)
	elif config.read_from:
		read_names.append("r/" + config.subreddit_name)

write_names.sort()
read_names.sort()
content = "=== Full Members ===\n\n* " + "\n\n* ".join(write_names) + "\n\n=== Read-Only ===\n\n* " + "\n\n* ".join(read_names)

f = open("database/subreddits.txt", "r")
old_content = f.read()
f.close()

# If we have added one or more new subs
if content != old_content:
	sub_page = wiki_helper.get_wiki_page(log_bot, WIKI_PAGE_NAME)
	sub_page.edit(content=content)

	f = open("database/subreddits.txt", "w")
	f.write(content)
	f.close()

	new_subs = [x for x in content.splitlines() if x not in old_content.splitlines()]
	discord.log("The following subs have joined the USL: \n\n* " + "\n* ".join(new_subs))
