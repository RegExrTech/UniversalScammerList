import sys
sys.path.insert(0, ".")
from Config import Config
import discord
import wiki_helper
import os
import tags

WIKI_PAGE_NAME = "public_tags"
log_bot = Config('logger')

content = "* " + "\n\n* ".join(tags.PUBLIC_TAGS)

sub_page = wiki_helper.get_wiki_page(log_bot, WIKI_PAGE_NAME)
print(content)
print(sub_page.content_md)
if content != sub_page.content_md:
	sub_page.edit(content=content)

	new_tags = [x for x in content.splitlines() if x not in sub_page.content_md.splitlines()]
	discord.log("The following new tags have been found: \n\n* " + "\n* ".join(new_tags))
