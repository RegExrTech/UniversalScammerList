import sys
sys.path.insert(0, ".")
from Config import Config
import wiki_helper
import os

WIKI_PAGE_NAME = "participating_subreddits"
log_bot = Config('logger')
snames = []

for fname in os.listdir("config"):
	sname = "r/" + fname.split(".")[0]
	snames.append(sname)

snames.sort()
content = "* " + "\n\n* ".join(snames)

f = open("database/subreddits.txt", "r")
old_content = f.read()
f.close()

# If we have added a new sub
if content != old_content:
	sub_page = wiki_helper.get_wiki_page(log_bot, WIKI_PAGE_NAME)
	sub_page.edit(content=content)

	f = open("database/subreddits.txt", "w")
	f.write(content)
	f.close()

