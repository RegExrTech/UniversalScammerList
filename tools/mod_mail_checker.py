import datetime
import os
import time
import traceback
import sys
sys.path.insert(0, '.')
from Config import Config
import discord

CONFIG = Config('logger')
NUN_MESSAGES = 100
FPATH = "static/mod_mail_message_timestamp.txt"
POST_LOOKBACK_LIMIT = 90


def get_mod_mail_messages(config, num_messages, after):
	queries = []
	try:
		queries += [x for x in config.subreddit_object.modmail.conversations(state='all', limit=num_messages, params={'before': after})]
	except Exception as e:
#		discord.log("Unable to read mod conversations from query on r/" + config.subreddit_name, e)
		print("Unable to read mod conversations from query on r/" + config.subreddit_name, e)
	return queries

def get_last_message_timestamp(fpath):
	f = open(fpath, 'r')
	id = f.read().strip()
	f.close()
	return float(id)

def save_last_message_timestamp(fpath, timestamp):
	f = open(fpath, 'w')
	f.write(str(timestamp))
	f.close()

def get_post_info(requesting_sub_object, post_lookback_limit):
	now = time.time()
	lookback_time = now - (post_lookback_limit * 24 * 60 * 60)
	posts = requesting_sub_object.new(limit=None)
	post_authors = set([])
	post_count = 0
	for post in posts:
		if post.created_utc < lookback_time:
			break
		post_count += 1
		if post.author:
			post_authors.add(post.author.name)
	return post_authors, post_count


def build_response(message, config, post_lookback_limit, all_configs):
	subject = message.subject.lower()
	body = message.messages[0].body_markdown.lower()
	author = message.messages[0].author
	requesting_sub = None
	for line in body.splitlines():
		if 'r/' in line:
			requesting_sub = line.split("r/")[1].split(" ")[0]
			if not requesting_sub or 'universalscammerlist' in requesting_sub:
				requesting_sub = None
				continue
			break
	if not requesting_sub:
		return "No requesting sub found. Archiving.", True
	requesting_sub_object = config.reddit.subreddit(requesting_sub)
	try:
		post_authors, post_count = get_post_info(requesting_sub_object, post_lookback_limit)
	except Exception as e:
		discord.log("Failed to get post statistics from r/" + requesting_sub, e, traceback.format_exc())
		return "I was unable to process post stats for r/" + requesting_sub + ". Please verify their status manually.", False
	if post_count >= 1000:
		post_count_string = "1000+"
	else:
		post_count_string = str(post_count)
	try:
		requester_is_mod = author in requesting_sub_object.moderator()
	except Exception as e:
		discord.log("Failed to get mod status of u/" + author.name + " in r/" + requesting_sub, e)
		return "Failed to get mod status of u/" + author.name + " in r/" + requesting_sub + ". Please verify their status manually.", False
	sub_has_usl_access_string_parts = []
	for other_config in all_configs:
		if other_config.subreddit_name != requesting_sub:
			continue
		if other_config.read_from:
			sub_has_usl_access_string_parts.append("Read")
		if other_config.write_to:
			sub_has_usl_access_string_parts.append("Write")
	if not sub_has_usl_access_string_parts:
		sub_has_usl_access_string_parts.append("False")
	response_parts = []
	response_parts.append("Requester: u/" + author.name)
	response_parts.append("Subreddit: r/" + requesting_sub)
	response_parts.append("Requester is mod of sub: " + str(requester_is_mod))
	response_parts.append("Sub already has USL access: " + ", ".join(sub_has_usl_access_string_parts))
	response_parts.append("Num posts in last " + str(post_lookback_limit) + " days: " + post_count_string)
	response_parts.append("Num unique post authors: " + str(len(post_authors)))
	response = "\n".join(["* " + part for part in response_parts])
	return response.strip(), False

def reply(message, response, should_archive):
	message.reply(body=response, internal=True)
	if should_archive:
		message.archive()


def main(config, num_messages, last_timestamp_file_path, post_lookback_limit):
	subnames = [x.split(".")[0] for x in os.listdir("config/")]
	all_configs = [Config(subname) for subname in subnames if subname]
	last_message_timestamp = get_last_message_timestamp(last_timestamp_file_path)
	messages = get_mod_mail_messages(config, num_messages, last_message_timestamp)
	newest_message_timestamp = last_message_timestamp
	for message in messages[::-1]:
		mod_conv_time = float(datetime.datetime.strptime(message.messages[0].date, "%Y-%m-%dT%H:%M:%S.%f%z").timestamp())
		if mod_conv_time <= last_message_timestamp:
			continue
		if mod_conv_time > newest_message_timestamp:
			newest_message_timestamp = mod_conv_time
		subject = message.subject.lower()
		if "we would like to join the usl" not in subject:
			continue
		response, should_archive = build_response(message, config, post_lookback_limit, all_configs)
		try:
			reply(message, response, should_archive)
		except Exception as e:
			discord.log("Unable to reply to message https://mod.reddit.com/mail/thread/" + message.id, e, traceback.format_exc())
	if newest_message_timestamp != last_message_timestamp:
		save_last_message_timestamp(last_timestamp_file_path, newest_message_timestamp)

if __name__ == '__main__':
	try:
		main(CONFIG, NUN_MESSAGES, FPATH, POST_LOOKBACK_LIMIT)
	except Exception as e:
		discord.log("Failed to run the mod mail tool", e, traceback.format_exc())
