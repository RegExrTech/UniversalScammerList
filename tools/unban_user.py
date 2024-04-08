import sys
sys.path.insert(0, '.')
import Config
import helper
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('username', metavar='C', type=str)
args = parser.parse_args()
user = args.username.lower()

subs = helper.get_all_subs(error_on_failure=True)

for _, sub_config in subs.items():
	if not sub_config.read_from and not sub_config.write_to:
		continue
	try:
		sub_config.subreddit_object.banned.remove(user)
		print("Unbanned on r/" + sub_config.subreddit_name)
	except Exception as e:
		print("Failed to unban on r/" + sub_config.subreddit_name + " with error " + str(e))
