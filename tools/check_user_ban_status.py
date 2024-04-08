import argparse
import sys
sys.path.insert(0, ".")
import helper

parser = argparse.ArgumentParser()
parser.add_argument('username', metavar='C', type=str)
args = parser.parse_args()
user = args.username.lower()

subs = helper.get_all_subs(error_on_failure=True)

for _, sub_config in subs.items():
	if not sub_config.read_from and not sub_config.write_to:
		continue
	ban_note = ""
	try:
		ban_note = "".join([ban.note for ban in sub_config.subreddit_object.banned(redditor=user)]).lower()
	except:
		print("Error for " + sub_config.subreddit_name)
	if ban_note:
		print(user + " is BANNED from " + sub_config.subreddit_name + "\n\tNote: " + ban_note)
	else:
		print(user + " is not banned from " + sub_config.subreddit_name)
