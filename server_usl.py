import json
import copy
from flask import Flask, request, jsonify
from werkzeug.serving import WSGIRequestHandler
import helper
from Config import Config
import datetime
import time

import sys
sys.path.insert(0, '.')
from tags import TAGS

app = Flask(__name__)

class JsonHelper:
        def ascii_encode_dict(self, data):
                ascii_encode = lambda x: x.encode('ascii') if isinstance(x, unicode) else x
                return dict(map(ascii_encode, pair) for pair in data.items())

        def get_db(self, fname, encode_ascii=True):
                with open(fname) as json_data:
                        if encode_ascii:
                                data = json.load(json_data, object_hook=self.ascii_encode_dict)
                        else:
                                data = json.load(json_data)
                return data

        def dump(self, db, fname):
                with open(fname, 'w') as outfile:
                        outfile.write(str(db).replace("'", '"').replace('{u"', '{"').replace('[u"', '["').replace(' u"', ' "').encode('ascii','ignore'))

json_helper = JsonHelper()
log_bot = Config('logger')

bans_fname = 'database/bans.json'
update_times_fname = 'database/update_times.json'
action_queue_fname = 'database/action_queue.json'

def get_most_recent_ban_time(user_data):
	# Gets the most recent ban date for each ban tag
	return max([user_data[tag]['issued_on'] for tag in user_data.keys()])

def order_users_by_ban_date(bans, reverse=False):
	# Returns a list of usernames sorted from oldest to newest ban.
	# Set reverse=True to get bans from newest to oldest.
	users_to_ban_date = {}
	for user in bans.keys():
		users_to_ban_date[user] = get_most_recent_ban_time(bans[user])
	return sorted(users_to_ban_date, key=users_to_ban_date.get, reverse=reverse)

def create_paginated_wiki(wiki_title, text_lines, config):
	content_size = 0
	page = 1
	page_content = {}
	index_start = 0
	index_end = 0
	for line in text_lines:
		content_size += len((line+"\n").encode('utf-8'))
		# Wiki pages are limited to 524288 bytes
		if content_size >= 400000:
			page_content[page] = "\n".join(text_lines[index_start:index_end])
			index_start = index_end
			page += 1
			content_size = len((line+"\n").encode('utf-8'))
		index_end += 1
	page_content[page] = "\n".join(text_lines[index_start:])

	page_numbers = page_content.keys()
	page_numbers.sort()
	for page_number in page_numbers:
		page = config.subreddit_object.wiki[wiki_title+"/"+str(page_number)]
		page.edit(page_content[page_number])
	page = config.subreddit_object.wiki[wiki_title]
	page.edit("\n".join(["* [Page " + str(page_number) + "](https://www.reddit.com/r/" + config.subreddit_name + "/wiki/" + wiki_title + "/" + str(page_number) + ")" for page_number in page_numbers]))

def update_action_log_wiki(action_text, config):
	index_page = config.subreddit_object.wiki['bot_actions']
	index_content = index_page.content_md
	latest_page_number = index_content.splitlines()[-1].split("/")[-1]

	content_page = config.subreddit_object.wiki['bot_actions/'+latest_page_number]
	page_content = content_page.content_md
	# Wiki pages are limited to 524288 bytes
	if len((action_text + "\n" + page_content).encode('utf-8')) < 400000:
		content_page.edit(action_text + "\n" + page_content)
	else:  # Make a new page
		latest_page_number = str(int(latest_page_number) + 1)
		config.subreddit_object.wiki.create(name='bot_actions/'+latest_page_number, content=action_text)
		index_page.edit(index_content + "\n" + "* https://www.reddit.com/r/" + config.subreddit_name + "/wiki/bot_actions/" + latest_page_number)

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
		update_action_log_wiki(action_text, log_bot)
	except Exception as e:
		print("Unable to log action " + action_text + " with error " + str(e))
	# Update the ban list
	sorted_usernames = order_users_by_ban_date(bans)
	text_lines = ["* /u/"+name+" " + " ".join(["#"+tag for tag in bans[name].keys()]) for name in sorted_usernames]
	try:
		create_paginated_wiki('banlist', text_lines, log_bot)
	except Exception as e:
		print("Unable to update the banlist with error " + str(e))

def clean_tags(tags):
	cleaned_tags = []
	for tag in tags:
		tag = tag.strip().replace("#", "").lower()
		if tag in TAGS:
			cleaned_tags.append(tag)
	return cleaned_tags

def add_sub_to_action_queue(sub_name, action_queue):
	action_queue[sub_name] = {'ban': {}, 'unban': {}}

def get_valid_moderators(sub_name, include_usl_mods=True):
	sub_config = helper.get_all_subs()[sub_name]
	moderators = [x.name.lower() for x in sub_config.subreddit_object.moderator()]
	if include_usl_mods:
		usl_sub = sub_config.reddit.subreddit('UniversalScammerList')
		moderators += [x.name.lower() for x in usl_sub.moderator()]
	return list(set(moderators))

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
	for tag in tags:
		if tag in bans[banned_user]:
			continue
		bans[banned_user][tag] = {'banned_by': banned_by, 'banned_on': banned_on, 'issued_on': issued_on, 'description': description}
		for sub_name in action_queue:
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
			# If the user is not already in the action queue for that tag
			if banned_user not in action_queue[sub_name]['ban'][tag]:
				action_queue[sub_name]['ban'][tag].append(banned_user)

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
			if user not in bans:
				continue
			to_return[tag][user] = bans[user][tag]
	for tag in action_queue[sub_name]['ban']:
		action_queue[sub_name]['ban'][tag] = []
	json_helper.dump(action_queue, action_queue_fname)
	return jsonify(to_return)

@app.route('/publish-unban/', methods=["POST"])
def publish_unban():
	global bans
	global action_queue
	unbanned_user = request.form["unbanned_user"].lower()
	tags = clean_tags(request.form["tags"].lower().split(","))
	requester = request.form["requester"].lower()
	if not tags:
		return jsonify({'error': 'No valid tags were provided.'})
	if unbanned_user not in bans:
		return jsonify({'error': 'u/' + unbanned_user + ' is not on the USL'})
	found_valid_tag = False
	issued_by_valid_mod = False
	correct_ban_issuers = {}
	valid_tags = []
	originally_banned_on_list = [bans[unbanned_user][tag]['banned_on'] for tag in tags]
	for tag in tags:
		if tag in bans[unbanned_user]:
			found_valid_tag = True
			# Get the list of moderators of the sub from which this user was banned.
			moderators = []
			for originally_banned_on in originally_banned_on_list:
				moderators += get_valid_moderators(originally_banned_on)
			if requester in moderators:
				del(bans[unbanned_user][tag])
				issued_by_valid_mod = True
				valid_tags.append(tag)
			else:
				correct_ban_issuers[tag] = originally_banned_on
	if not found_valid_tag:
		return jsonify({'error': 'u/' + unbanned_user + ' is not currently banned with any of the given tags. The valid tags are:\n\n' + "\n".join(["* #" + tag for tags in bans[unbanned_user].keys()])})
	if not issued_by_valid_mod:
		error_text = 'Sorry, but this user could not be unbanned because you are not a moderator of any subs that issued a ban for any of the given tags. The following tags may only be removed by the mods of the following subreddits:'
		for key, value in correct_ban_issuers.items():
			error_text += "\n\n* \#" + key + " issued by r/" + value
		return jsonify({'error': error_text})
	if not bans[unbanned_user]:
		del(bans[unbanned_user])
	all_subs = helper.get_all_subs()
	for sub_name in action_queue:
		for tag in valid_tags:
			if tag not in action_queue[sub_name]['unban']:
				action_queue[sub_name]['unban'][tag] = []
			remaining_tags = []
			if unbanned_user in bans:
				remaining_tags = bans[unbanned_user].keys()
			# ONLY issue an unban IF this user has no tags remaining that the sub is subscribed to.
			if not any([x in remaining_tags for x in all_subs[sub_name].tags]):
				if unbanned_user not in action_queue[sub_name]['unban'][tag]:
					action_queue[sub_name]['unban'][tag].append(unbanned_user)

	log_action(unbanned_user, requester, originally_banned_on, time.time(), context="Tags Removed: " + ", ".join(["#" + _tag for _tag in valid_tags]), is_unban=True)
        json_helper.dump(bans, bans_fname)
	json_helper.dump(action_queue, action_queue_fname)
	return jsonify({})

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

@app.route('/get-unban-queue/', methods=["GET"])
def get_unban_queue():
	global action_queue
        sub_name = request.form["sub_name"].lower()
	tags = request.form["tags"].lower().split(",")
        if sub_name not in action_queue:
                add_sub_to_action_queue(sub_name, action_queue)
	to_unban = copy.deepcopy(action_queue[sub_name]['unban'])
	for tag in to_unban.keys():
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
	return jsonify({'update_time': time.time()})

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


if __name__ == "__main__":
        try:
                bans = json_helper.get_db(bans_fname)
                update_times = json_helper.get_db(update_times_fname)
		action_queue = json_helper.get_db(action_queue_fname)
                app.run(host= '0.0.0.0', port=8080, request_handler=MyRequestHandler)
        except Exception as e:
		print(e)
                pass
