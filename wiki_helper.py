from Config import Config
from prawcore.exceptions import NotFound
import time

WIKI_PAGE_NAME = 'usl_config'

def run_config_checker(config):
	# Get the config page
	try:
		config_page = config.subreddit_object.wiki[WIKI_PAGE_NAME]
	except:
		# Transient error, assume no changes have been made
		return
	# If the config page does not exist, make it
	try:
		content = config_page.content_md
	except NotFound as e:
		try:
			create_wiki_config(config, config_page)
		except NotFound as e:
			# We likely don't have permissions, so just silently return
			return
	except:
		# Transient error, assume no changes have been made
		return
	# If the bot was the last person to update the config, break out early
	if config_page.revision_by.name.lower() == config.bot_username.lower():
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
	# Inform parsing successful
	inform_config_valid(config_page)
	# Validate Wiki Page
	validate_wiki_content(config, config_page)

def create_wiki_config(config, config_page):
	validate_wiki_content(config, config_page)
	config_page.mod.update(listed=False, permlevel=2)

def validate_wiki_content(config, config_page):
	content = "tags:" + ",".join(["#"+tag for tag in config.tags]) + "\n\nbot_timestamp:" + str(time.time())
	config_page.edit(content)

def get_config_content(content):
	config_content = {}
	for line in content.splitlines():
		key = line.split(":")[0]
		value = ":".join(line.split(":")[1:])
		config_content[key] = value
	return config_content

def invalidate_config(content):
	content = "\n\n".join(content.split("\n\n")[1:] + ["bot_timestamp:" + str(time.time())])
	config_page.edit(content)

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
	config.tags = tags
	config.update_config()

if __name__ == "__main__":
	log_bot = Config('logger')
	run_config_checker(log_bot)