import os
from Config import Config
subs = {}

def get_all_subs(error_on_failure=False):
	global subs
	files = os.listdir('config')
	for file in files:
		if ".swp" == file[-4:]:
			continue
		try:
			sub = Config(file.split(".")[0])
		except Exception as e:
			if error_on_failure:
				raise e
			# If we can't get the store, it's usually because I'm manually editing the file
			# so, instead, just used the cached version of the store
			continue
		subs[sub.subreddit_name] = sub
	return subs
