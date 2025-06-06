import json
import copy
from flask import Flask, request, jsonify
from werkzeug.serving import WSGIRequestHandler
import helper
from Config import Config
import datetime
import time
import prawcore

import sys
sys.path.insert(0, '.')
from tags import TAGS
from tags import PRIVATE_TAGS
from tags import PUBLIC_TAGS

app = Flask(__name__)

class JsonHelper:
	def get_db(self, fname):
		with open(fname) as json_data:
			data = json.load(json_data)
		return data

	def dump(self, db, fname):
		with open(fname, 'w') as outfile:
			outfile.write(json.dumps(db, sort_keys=True, indent=4))

json_helper = JsonHelper()
log_bot = Config('logger')

bans_fname = 'database/bans.json'
update_times_fname = 'database/update_times.json'
action_queue_fname = 'database/action_queue.json'

def update_user_wiki(username, tags, action_text, config):
	try:
		content_page = config.subreddit_object.wiki['database/'+username]
		old_data = content_page.content_md.splitlines()[1:]
	except prawcore.exceptions.NotFound:
		config.subreddit_object.wiki.create(name='database/'+username, content="")
		old_data = []
	page_content_lines = ["* tags: " + ", ".join(tags)]
	page_content_lines += old_data
	page_content_lines.append(action_text)
	page_content = "\n".join(page_content_lines)
	content_page.edit(content=page_content)

def log_action(impacted_user, issued_by, originated_from, issued_at, context="", is_ban=False, is_unban=False):
	# Generate new action text
	action_text = "* u/" + impacted_user + " was "
	if is_ban:
		action_text += "banned"
	elif is_unban:
		action_text += "unbanned"
	else:
		action_text += "<unknown action>"
	action_text += " on " + datetime.datetime.fromtimestamp(issued_at).strftime("%Y-%m-%d %H:%M") + " UTC"
#	action_text += " by u/" + issued_by
	action_text += " from r/" + originated_from
	if context != "":
		action_text += " with context - " + context
	# Update action log
	try:
		# Only update if the context includes a public tag
		if any(["#"+tag in context for tag in PUBLIC_TAGS]):
			if impacted_user in bans:
				tags = [tag for tag in list(bans[impacted_user].keys()) if tag in PUBLIC_TAGS]
			else:
				tags = []
			update_user_wiki(impacted_user, tags, action_text, log_bot)
			time.sleep(5)  # Sleep a bit so we don't rate limit ourselves when writing to wiki pages
	except Exception as e:
		print("Unable to log action " + action_text + " with error " + str(e))

def clean_tags(tags):
	cleaned_tags = []
	for tag in tags:
		tag = tag.strip().replace("#", "").lower()
		if tag in TAGS:
			cleaned_tags.append(tag)
	return cleaned_tags

def add_sub_to_action_queue(sub_name, action_queue):
	action_queue[sub_name] = {'ban': {}, 'unban': {}}
	sub_config = helper.get_all_subs()[sub_name]
	for tag in sub_config.tags:
		action_queue[sub_name]['ban'][tag] = []
	for user in bans:
		for tag in bans[user]:
			if tag in action_queue[sub_name]['ban']:
				action_queue[sub_name]['ban'][tag].append(user)

def get_valid_moderators(sub_name, include_usl_mods=False):
	sub_name = sub_name.lower()
	all_sub_configs = helper.get_all_subs()
	sub_config = all_sub_configs[sub_name]
	moderators = [x.name.lower() for x in sub_config.subreddit_object.moderator()]
	if include_usl_mods:
		usl_sub = all_sub_configs['universalscammerlist']
		moderators += [x.name.lower() for x in usl_sub.subreddit_object.moderator()]
	return list(set(moderators + ['regexr']))

@app.route('/subscribe-new-tags/', methods=["POST"])
def subscribe_new_tags():
	global action_queue
	sub_name = request.form["sub_name"]
	tags = request.form["tags"].lower().split(",")
	for tag in tags:
			action_queue[sub_name]['ban'][tag] = []
	for user in bans:
		for tag in bans[user]:
			if tag in tags:
				action_queue[sub_name]['ban'][tag].append(user)
	return jsonify({})

@app.route('/publish-ban/', methods=["POST"])
def publish_ban():
	global bans
	global action_queue
	sub_configs = helper.get_all_subs()
	banned_user = request.form["banned_user"].lower()
	banned_by = request.form["banned_by"].lower()
	banned_on = request.form["banned_on"].lower()
	description = request.form["description"]
	try:
		issued_on = float(request.form["issued_on"])
	except:
		return jsonify({'error': 'issued_on must be an float representing the UNIX timestamp when the ban originated.'})
	tags = clean_tags(request.form["tags"].lower().split(","))
	if not tags:
		return jsonify({'error': 'No actual tags could be found.'})

	if banned_user not in bans:
		bans[banned_user] = {}
	duplicate_ban = True
	for tag in tags:
		if tag in bans[banned_user]:
			continue
		duplicate_ban = False
		bans[banned_user][tag] = {'banned_by': banned_by, 'banned_on': banned_on, 'issued_on': issued_on, 'description': description}
		for sub_name in action_queue:
			if sub_name not in sub_configs:
				continue
			sub_config = sub_configs[sub_name]
			# If this is the reporting sub
			if sub_name == banned_on:
				continue
			# If this sub is not subscribed to this tag
			if tag not in sub_config.tags:
				continue
			# If the tag doesn't already exist in the action queue
			if tag not in action_queue[sub_name]['ban']:
				action_queue[sub_name]['ban'][tag] = []
			if tag not in action_queue[sub_name]['unban']:
				action_queue[sub_name]['unban'][tag] = []
			# If the user is in the queue to be unbanned but a request to ban them happened
			# before the unban could take effect, remove the unban request and do nothing.
			if banned_user in action_queue[sub_name]['unban'][tag]:
				action_queue[sub_name]['unban'][tag].remove(banned_user)
			# If the user is not already in the ban action queue for that tag
			elif banned_user not in action_queue[sub_name]['ban'][tag]:
				action_queue[sub_name]['ban'][tag].append(banned_user)
	if not duplicate_ban:
		log_action(banned_user, banned_by, banned_on, issued_on, context=description + " - Tags Added: " + ", ".join(["#" + _tag for _tag in tags]), is_ban=True)
	json_helper.dump(bans, bans_fname)
	json_helper.dump(action_queue, action_queue_fname)
	return jsonify({})

@app.route('/get-ban-queue/', methods=["GET"])
def get_ban_queue():
	global action_queue
	sub_name = request.form["sub_name"].lower()
	if sub_name not in action_queue:
		add_sub_to_action_queue(sub_name, action_queue)
	to_return = {}
	for tag in action_queue[sub_name]['ban']:
		to_return[tag] = {}
		for user in action_queue[sub_name]['ban'][tag]:
			# If we can't find the relevant information on the user in the DB, then they aren't someone we should actually ban.
			if user not in bans:
				continue
			if tag not in bans[user]:
				continue
			to_return[tag][user] = bans[user][tag]
	for tag in action_queue[sub_name]['ban']:
		action_queue[sub_name]['ban'][tag] = []
	json_helper.dump(action_queue, action_queue_fname)
	return jsonify(to_return)

@app.route('/publish-unban/', methods=["POST"])
def publish_unban():
	# TODO The bot is unclear when a mod goes to remove multiple tags if they are only authorized to remove *some* of those tags.
	# For example, if a user is banned with #scammer and #sketchy but I'm only authorized to remove #sketchy but a sent a request
	# to remove both tags anyway, the bot will say that my request went through as expected EVEN THOUGH it really only removed
	# the tags that I'm authorized to remove.
	#
	# The bot should be clearer about what it did for each tag that has been requested to be removed.
	global bans
	global action_queue
	requester = request.form["requester"].lower()
	unbanned_user = request.form["unbanned_user"].lower()
	tags_string = request.form["tags"].lower()
	unbanning_sub = request.form["unbanning_sub"].lower()
	if unbanned_user not in bans:
		if tags_string == 'all':
			return jsonify({'silent': True})
		return jsonify({'error': 'u/' + unbanned_user + ' is not on the USL'})
	all_subs = helper.get_all_subs()
	# If the ban came from a mod log unban, we want to avoid putting another unban action in that sub's
	# action queue.
	suppress_requesting_sub = False
	if tags_string == 'all':
		if unbanned_user in bans:
			tags = list(bans[unbanned_user].keys())
		else:
			return jsonify({'silent': True})
		# In the event that "all" tags are requested to be removed, we only want to remove tags that
		# the requesting sub applied to the user in question.
		tags = [tag for tag in bans[unbanned_user] if unbanning_sub == bans[unbanned_user][tag]['banned_on']]
		if not tags:
			return jsonify({'silent': True})
		suppress_requesting_sub = True
	else:
		tags = clean_tags(tags_string.split(","))
	if not tags:
		return jsonify({'error': 'No valid tags were provided.'})
	found_valid_tag = False
	issued_by_valid_mod = False
	correct_ban_issuers = {}
	valid_tags = []
	originally_banned_on = ""
	for tag in tags:
		if tag not in bans[unbanned_user]:
			continue
		found_valid_tag = True
		valid_mods = get_valid_moderators(bans[unbanned_user][tag]['banned_on'].lower())
		if requester in valid_mods:
			originally_banned_on = bans[unbanned_user][tag]['banned_on'].lower()
			del(bans[unbanned_user][tag])
			issued_by_valid_mod = True
			valid_tags.append(tag)
		else:
			correct_ban_issuers[tag] = bans[unbanned_user][tag]['banned_on']
	if not found_valid_tag:
		return jsonify({'error': 'u/' + unbanned_user + ' is not currently banned with any of the given tags. The valid tags are:\n\n' + "\n".join(["* #" + tag for tag in list(bans[unbanned_user].keys())])})
	if not issued_by_valid_mod:
		error_text = 'Sorry, but this user could not be unbanned because you are not a moderator of any subs that issued a ban for any of the given tags. The following tags may only be removed by the mods of the following subreddits:'
		for key, value in correct_ban_issuers.items():
			error_text += "\n\n* \#" + key + " issued by r/" + value
		return jsonify({'error': error_text})
	if not bans[unbanned_user]:
		del(bans[unbanned_user])
	for sub_name in action_queue:
		# Sometimes we remove subs but they stay in the action queue
		if sub_name not in all_subs:
			continue
		# If the unban came from the mod log, avoid putting an unban in that sub's action queue.
		if suppress_requesting_sub and sub_name == unbanning_sub:
			continue
		for tag in valid_tags:
			# If this sub is not subscribed to this tag
			if tag not in all_subs[sub_name].tags:
				continue
			if tag not in action_queue[sub_name]['unban']:
				action_queue[sub_name]['unban'][tag] = []
			remaining_tags = []
			if unbanned_user in bans:
				remaining_tags = list(bans[unbanned_user].keys())
			# ONLY issue an unban IF this user has no tags remaining that the sub is subscribed to.
			if not any([x in remaining_tags for x in all_subs[sub_name].tags]):
				# If the user was scheduled to be banned but the unban request came through BEFORE
				# the user could even be banned on the sub, then skip the ban step and just remove them
				# from the queue
				if tag in action_queue[sub_name]['ban'] and unbanned_user in action_queue[sub_name]['ban'][tag]:
					action_queue[sub_name]['ban'][tag].remove(unbanned_user)
				elif unbanned_user not in action_queue[sub_name]['unban'][tag]:
					action_queue[sub_name]['unban'][tag].append(unbanned_user)

	log_action(unbanned_user, requester, originally_banned_on, time.time(), context="Tags Removed: " + ", ".join(["#" + _tag for _tag in valid_tags]), is_unban=True)
	json_helper.dump(bans, bans_fname)
	json_helper.dump(action_queue, action_queue_fname)
	return jsonify({'tags': ", ".join(["#" + _tag for _tag in valid_tags])})

@app.route('/add-to-action-queue/', methods=["POST"])
def add_to_action_queue():
	global action_queue
	sub_name = request.form["sub_name"].lower()
	username = request.form["username"].lower()
	action = request.form["action"].lower()
	tags = request.form["tags"].lower().split(",")
	if sub_name not in action_queue:
		action_queue[sub_name] = {}
	if action not in action_queue[sub_name]:
		action_queue[sub_name][action] = {}
	for tag in tags:
		if tag not in action_queue[sub_name][action]:
			action_queue[sub_name][action][tag] = []
		if username not in action_queue[sub_name][action][tag]:
			action_queue[sub_name][action][tag].append(username)
	json_helper.dump(action_queue, action_queue_fname)
	return jsonify({})

@app.route('/remove-sub-from-action-queue/', methods=["POST"])
def remove_sub_from_action_queue():
	global action_queue
	sub_name = request.form["sub_name"].lower()
	if sub_name in action_queue:
		del(action_queue[sub_name])
	json_helper.dump(action_queue, action_queue_fname)
	return jsonify({})

@app.route('/get-unban-queue/', methods=["GET"])
def get_unban_queue():
	global action_queue
	sub_name = request.form["sub_name"].lower()
	tags = request.form["tags"].lower().split(",")
	if sub_name not in action_queue:
		add_sub_to_action_queue(sub_name, action_queue)
	to_unban = copy.deepcopy(action_queue[sub_name]['unban'])
	for tag in list(to_unban.keys()):
		if tag not in tags:
			del(to_unban[tag])
	for tag in action_queue[sub_name]['unban']:
		action_queue[sub_name]['unban'][tag] = []
	json_helper.dump(action_queue, action_queue_fname)
	return jsonify(to_unban)

@app.route('/get-ban-data/', methods=["GET"])
def get_ban_data():
	banned_user = request.form["banned_user"].lower()
	if banned_user in bans:
		return jsonify(bans[banned_user])
	return jsonify({})

@app.route('/get-last-update-time/', methods=["GET"])
def get_last_update_time():
	sub_name = request.form["sub_name"].lower()
	if sub_name in update_times:
		return jsonify({'update_time': update_times[sub_name]})
	return jsonify({'update_time': 0})

@app.route('/set-last-update-time/', methods=["POST"])
def set_last_update_time():
	global update_times
	sub_name = request.form["sub_name"].lower()
	try:
		update_time = float(request.form["update_time"])
	except:
		return jsonify({'error': 'update_time must be an float representing the UNIX timestamp.'})
	update_times[sub_name] = update_time
	json_helper.dump(update_times, update_times_fname)
	return jsonify({})

@app.route('/dump/', methods=["POST"])
def dump():
	json_helper.dump(bans, bans_fname)
	json_helper.dump(update_times, update_times_fname)
	json_helper.dump(action_queue, action_queue_fname)
	return jsonify({})


class MyRequestHandler(WSGIRequestHandler):
	# Just like WSGIRequestHandler, but without "code"
	def log_request(self, code='-', size='-'):
		if 200 == code:
			pass
		else:
			self.log('info', '"%s" %s %s', self.requestline, code, size)


def port_in_use(port):
	import socket
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		return s.connect_ex(('0.0.0.0', PORT)) == 0

if __name__ == "__main__":
	try:
		PORT = 8080
		if not port_in_use(PORT):
			bans = json_helper.get_db(bans_fname)
			update_times = json_helper.get_db(update_times_fname)
			action_queue = json_helper.get_db(action_queue_fname)
			print("Server start time: " + str(time.time()))
			app.run(host= '0.0.0.0', port=PORT, request_handler=MyRequestHandler)
	except Exception as e:
		print(e)
		pass
