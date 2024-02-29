from Config import Config, dump
from prawcore.exceptions import NotFound
import time
import requests
import sys
sys.path.insert(0, ".")
import discord

WIKI_PAGE_NAME = 'usl_config'
request_url = "http://0.0.0.0:8080"

def get_wiki_page(config, wiki_page_name):
	# Get the config page
	try:
		return config.subreddit_object.wiki[wiki_page_name]
	except:
		# Transient error, assume no changes have been made
		return None

def get_wiki_page_content(config_page, config):
	# If the config page does not exist, make it
	try:
		return config_page.content_md
	except NotFound as e:
		try:
			create_wiki_config(config, config_page)
			return config_page.content_md
		except NotFound as e:
			# We likely don't have permissions, so just silently return
			return ""
	except:
		# Transient error, assume no changes have been made
		return ""

def run_config_checker(config):
	config_page = get_wiki_page(config, WIKI_PAGE_NAME)
	content = get_wiki_page_content(config_page, config)
	if content == "":
		return
	# If the bot was the last person to update the config, break out early
	if config_page.revision_by.name.lower() == config.bot_username.lower():
		# But if there are local edits to the config, copy them to the remote config first
		if not wiki_page_is_equal(config, content):
			print("    Updated config for r/" + config.subreddit_name + " due to local changes.")
			validate_wiki_content(config, config_page)
		return
	# Parse the config page
	try:
		config_content = get_config_content(content)
	except:
		# Unable to parse the config
		invalidate_config(content)
		inform_config_invalid(config_page)
		return
	# Update the tags
	if 'tags' in config_content:
		update_tags(config_content['tags'], config)
	if 'typo_checking' in config_content:
		typo_checking = config_content['typo_checking'].lower() == 'true'
		config.update_typo_checking(typo_checking, config)
	if 'local_unban_is_usl_unban' in config_content:
		local_unban_is_usl_unban = config_content['local_unban_is_usl_unban'].lower() == 'true'
		config.update_local_unban_config(local_unban_is_usl_unban)
	if 'usl_rep' in config_content and config.write_to:
		log_bot = Config('logger')
		usl_mods = set([x.name.lower() for x in log_bot.subreddit_object.moderator()])
		mods = [x.name.lower() for x in config.subreddit_object.moderator()]
		usl_rep = config_content['usl_rep'].split('/')[-1].lower()
		# An invalid user was added as a USL rep
		if usl_rep not in mods or usl_rep not in usl_mods:
			invalidate_config(content)
			inform_config_invalid(config_page)
			return
		config.update_usl_rep(usl_rep)
	# Inform parsing successful
	inform_config_valid(config_page)
	# Validate Wiki Page
	validate_wiki_content(config, config_page)
	discord.log("u/" + config_page.revision_by.name + " has updated the r/" + config.subreddit_name + " config page.\n\n---\n\nOld Content: " + get_local_config_content(config) + "\n\n---\n\nNew Content: " + content)
	print("    u/" + config_page.revision_by.name + " has updated the r/" + config.subreddit_name + " config page.")

def create_wiki_config(config, config_page):
	validate_wiki_content(config, config_page)
	config_page.mod.update(listed=False, permlevel=2)

def get_local_config_content(config):
	content = "tags: " + ",".join(["#"+tag for tag in config.tags])
	content += "\n\ntypo_checking: " + str(config.typo_checking)
	content += "\n\nlocal_unban_is_usl_unban: " + str(config.local_unban_is_usl_unban)
	if config.write_to:
		content += "\n\nusl_rep: " + config.usl_rep
	return content

def validate_wiki_content(config, config_page):
	content = get_local_config_content(config)
	content += "\n\nbot_timestamp:" + str(time.time())
	content += "\n\nDocumentation: https://www.universalscammerlist.com/about"
	config_page.edit(content=content)

def wiki_page_is_equal(config, page_content):
	local_content = get_local_config_content(config)
	return local_content in page_content

def get_config_content(content):
	config_content = {}
	for line in content.splitlines():
		key = line.split(":")[0]
		value = ":".join(line.split(":")[1:]).strip()
		config_content[key] = value
	return config_content

def invalidate_config(content):
	content = "\n\n".join(content.split("\n\n")[1:] + ["bot_timestamp:" + str(time.time())])
	config_page.edit(content=content)

def inform_config_invalid(config_pag):
	message = "I'm sorry but I was unable to parse the config you set in the " + WIKI_PAGE_NAME + " wiki page. Please review the [config guide](https://www.universalscammerlist.com/config_guide.html) and try again."
	send_update_message(config_page, message)

def inform_config_valid(config_page):
	message = "I have successfully parsed the " + WIKI_PAGE_NAME + " wiki page and updated my config. Thank you for your contribution!"
	send_update_message(config_page, message)

def send_update_message(config_page, message):
	redditor = config_page.revision_by
	username = redditor.name
	message = "Hi u/" + username + "\n\n" + message
	redditor.message(subject=WIKI_PAGE_NAME + " wiki update", message=message)

def update_tags(tags_string, config):
	tags_string = tags_string.strip()
	tags = tags_string.split(",")
	tags = [tag.strip() for tag in tags]
	tags = [tag for tag in tags if tag != '']
	tags = [tag[1:] if tag[0] == "#" else tag for tag in tags]
	new_tags = [tag for tag in tags if tag not in config.tags]
	config.update_tags(tags)
	requests.post(request_url + "/subscribe-new-tags/", {'tags': ",".join(new_tags), 'sub_name': config.subreddit_name})

# ONLY RUN MANUALLY
def _add_value_to_configs():
	import os
	log_bot = Config('logger')
	usl_mods = set([x.name.lower() for x in log_bot.subreddit_object.moderator()])
	subnames = [x.split(".")[0] for x in os.listdir("config/")]
	for subname in subnames:
		config = Config(subname)

		if subname.lower() == 'PlayingCardsMarket'.lower():
			continue

		config.raw_config['usl_rep'] = ""
		if not config.write_to:
			dump(config.raw_config, "config/" + subname + ".json")
			continue
		mods = [x.name.lower() for x in config.subreddit_object.moderator()]
		rep = ""
		for mod in mods:
			if any([x in mod for x in ['automod', 'bot']]):
				continue
			if mod not in usl_mods:
				continue
			if subname.lower() != 'funkoswap' and mod == 'regexr':
				continue
			print("Rep of r/" + subname + " is u/" + mod)
			rep = mod
			break
		if not rep:
			print("NO USL REP found for r/" + subname)
		config.raw_config['usl_rep'] = rep
		dump(config.raw_config, "config/" + subname + ".json")
		config_page = get_wiki_page(config, WIKI_PAGE_NAME)
		validate_wiki_content(config, config_page)

if __name__ == "__main__":
#	log_bot = Config('logger')
#	run_config_checker(log_bot)

	_add_value_to_configs()
