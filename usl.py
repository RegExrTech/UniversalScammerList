import sys
sys.path.insert(0, '.')
from Config import Config
from tags import TAGS

import praw

from collections import defaultdict
import requests
import argparse

request_url = "http://0.0.0.0:8080"

DO_NOT_BAN = set(['[deleted]', 'automoderator'])

def get_ban_tags_and_description(description):
	tags = []
	other = []
	for word in [x for x in description.split(" ") if x]:
		if word[0] == "#":
			tags.append(word)
		else:
			other.append(word)
	description = " ".join(other)
	description = " ".join(description.split(":")[1:])
	return tags, description

def publish_bans(sub_config):
	last_update_time_data = requests.get(request_url + "/get-last-update-time/", data={'sub_name': sub_config.subreddit_name}).json()
	if 'update_time' in last_update_time_data:
		last_update_time = last_update_time_data['update_time']
	else:
		print("Error getting last_update_time from server: " + last_update_time_data['error'])
		return

	new_update_time = last_update_time
	# Get list of user bans
	try:
		actions = sub_config.subreddit_object.mod.log(limit=None, action='banuser')
	except Exception as e:
		print("Unable to get mod actions when checking for bans with error " + str(e))
		return
	for action in actions:
		if action.created_utc <= last_update_time:
			continue
		created_utc = action.created_utc
		description = action.description
		banned_by = action.mod
		banned_user = action.target_author
		# Ignore bans issued by the USL
		if sub_config.is_bot_name(banned_by.name):
			continue
		# Ignore temp bans
		if not str(action.details) == "permanent":
			continue
		ban_tags, description = get_ban_tags_and_description(description)
		# Ignore bans without USL tags
		if not ban_tags:
			continue
		requests.post(request_url + "/publish-ban/", {'banned_user': banned_user, 'banned_by': banned_by.name, 'banned_on': sub_config.subreddit_name, 'issued_on': created_utc, 'tags': ",".join(ban_tags), 'description': description})
		if action.created_utc > new_update_time:
			new_update_time = action.created_utc

	if last_update_time != new_update_time:
		requests.post(request_url + "/set-last-update-time/", {'sub_name': sub_config.subreddit_name, 'update_time': new_update_time})

def ban_from_queue(sub_config):
	to_ban = requests.get(request_url + "/get-ban-queue/", data={'sub_name': sub_config.subreddit_name}).json()
	users_to_descriptions = defaultdict(lambda: {'description': '', 'mod note': ''})
	for tag in to_ban:
		if tag not in sub_config.tags:
			continue
		for user in to_ban[tag]:
			user_data = to_ban[tag][user]
			if user not in users_to_descriptions:
				users_to_descriptions[user]['mod note'] = "USL ban from r/" + user_data['banned_on'] + " - " + user_data['description'] + " - "
			users_to_descriptions[user]['mod note'] += "#" + tag + " "
			users_to_descriptions[user]['description'] = "You have been banned from r/" + sub_config.subreddit_name + " due to a ban from r/" + user_data['banned_on'] + ". You must contact the mods of r/" + user_data['banned_on'] + " to have this ban removed. Please do not reply to this message."
	for user in users_to_descriptions:
		text = users_to_descriptions[user]
		if user in DO_NOT_BAN:
			continue
		ban_note = "".join([ban.note for ban in sub_config.subreddit_object.banned(redditor=user)]).lower()
		if not any(["#"+_tag in ban_note for _tag in TAGS]):
			message_content = "Hello, mods of r/" + sub_config.subreddit_name + ". Recently, u/" + user + " was added to the USL with the following context: \n\n> " + text['mod note'] + "\n\nHowever, this user was previously banned on your subreddit through unrelated means. At this time, no action is required. The ban against this user on your sub is not being modified.\n\nHowever, if you wish to modify this ban to be in line with the USL, please modify the ban for this user to include the tags mentioned above. This will sync your ban with the USL so, if this user is taken off the USL in the future, they will be unbanned from your sub as well. If you do NOT wish for this to happen and want this user to remain banned, even if they are removed from the USL, then no action is needed on your part."
			sub_config.subreddit_object.message("Duplicate Ban Found By USL", message_content)
			continue
		try:
			sub_config.subreddit_object.banned.add(user, ban_message=text['description'][:1000], ban_reason="USL Ban", note=text['mod note'][:300])
		except Exception as e:
			print("Unable to ban u/" + user + " on r/" + sub_config.subreddit_name + " with error " + str(e))
		print(user + " - " + text['description'] + " - " + text['mod note'])

def get_messages(reddit):
	messages = []
	to_mark_as_read = []
	try:
		for message in reddit.inbox.unread():
			to_mark_as_read.append(message)
			if not message.was_comment:
				messages.append(message)
	except Exception as e:
		print(e)
		print("Failed to get next message from unreads. Ignoring all unread messages and will try again next time.")

	for message in to_mark_as_read:
		try:
			message.mark_read()
		except Exception as e:
			print(e)
			print("Unable to mark message as read. Leaving it as is.")

	return messages

def publish_unbans(sub_config):
	messages = get_messages(sub_config.reddit)
	for message in messages:
		requester = message.author.name.lower()
		text = message.body.strip().lower()
		words = text.split(" ")
		unbanned_user = ""
		tags = []
		command = ""
		for count, word in enumerate(words):
			word = word.strip()
			if not word:
				continue
			if word == "$unban":
				command = word
				if count + 1 < len(words):
					unbanned_user = words[count+1].split("/")[-1]
			elif word[0] == "#":
				tags.append(word[1:])
		if not command:
			text = "No command was found. Please be sure to start your message with a command. Commands should be in the form `$command`. For example, `$unban u/username #tag1 #tag2`"
		elif command == "$unban":
			if not unbanned_user:
				text = "No username was found following the command in your message. Please ensure that a username is present in your message. For example, `$unban u/username #tag1 #tag2`"
			elif not tags:
				text = "No tags were found in your message. Please ensure that tags start with a `#` character and include the tags you wish to remove from the USL. For example, `$unban u/username #tag1 #tag2`"
			else:
				# Send unban request to server. Check response for errors, like user not banned, or tag not recognized
				response = requests.post(request_url + "/publish-unban/", {'requester': requester, 'unbanned_user': unbanned_user, 'tags': ",".join(tags)}).json()
				if 'error' in response:
					text = response['error']
				else:
					text = "u/" + unbanned_user + " is being unbanned with the following tags: " + ", ".join(["#"+tag for tag in tags])
		else:
			text = "Handling for that command has not been implimented yet. Sorry."

		try:
			message.reply(text)
		except Exception as e:
			print(sub_config.bot_username + " could not reply to " + str(message.author) + " with error - " + str(e))

def unban_from_queue(sub_config):
	to_unban = requests.get(request_url + "/get-unban-queue/", data={'sub_name': sub_config.subreddit_name, 'tags': ",".join(sub_config.tags)}).json()
	users = []
	for tag in to_unban:
		users += to_unban[tag]
	for user in list(set(users)):
		ban_note = "".join([ban.note for ban in sub_config.subreddit_object.banned(redditor=user)]).lower()
		if not any(["#"+_tag in ban_note for _tag in TAGS]):
			message_content = "Hello, mods of r/" + sub_config.subreddit_name + ". Recently, u/" + user + " was removed from the USL. However, you banned this user for unrelated reasons. As such, I will not remove this ban for you. However, if you banned this user because you believed them to be a scammer, please double check things as the situation might have changed. Thanks!"
			sub_config.subreddit_object.message("Conflicting Unban Found In The USL", message_content)
			continue
		try:
			sub_config.subreddit_object.banned.remove(user)
		except Exception as e:
			print("Unable to unban u/" + user + " on r/" + sub_config.subreddit_name + " with error " + str(e))

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('sub_name', metavar='C', type=str)
	args = parser.parse_args()

	sub_config = Config(args.sub_name.lower())

	if sub_config.write_to:
		publish_bans(sub_config)
		publish_unbans(sub_config)
	if sub_config.read_from:
		ban_from_queue(sub_config)
		unban_from_queue(sub_config)


if __name__ == "__main__":
	main()
