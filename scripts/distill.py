import json
import requests
import hashlib
import sys
import sqlite3

# A local database to store the result of all queries 
#
# Schema: results(key text, turns text, results text)
#   - key: hash of the conversation
#   - turns: all human queries in the conversation
#   - results: llama-70b-chat result, together with human prompts
#              in a format that can be used for fine-tuning
#
con = sqlite3.connect("sharegpt.db")
cur = con.cursor()

# A file that contains all human prompts, in a format of
#   [["..", ".."], # first conversation
#    ["..", ".."]  # second conversation
#   ]
#
conversations = json.load(open(sys.argv[1]))

# output file
#
out_file = open(sys.argv[1] + "output.json", "w")

# Together API end point
endpoint = 'https://api.together.xyz/inference'
APIKEY = "PUT YOUR TOGETHER API KEY HERE"

# For each conversation
for turns in conversations:

	# Create a signature for the conversation 
	#
	m = hashlib.sha256()
	m.update(" ".join(turns).encode())
	key = m.hexdigest()

	# Check if this conversation is already in the database
	#   - If so, skip
	#   - Otherwise, query
	#
	res = cur.execute(f"SELECT results FROM results WHERE id='{key}';")
	fetched = res.fetchone()
	if fetched != None:
		continue

	failed = 0   # has the querying process ever fail 
	prompt = ""  # prompt

	# for each human query in the conversation
  #
	for turn in turns:

		# create the prompt by appending human query
		#
		prompt = prompt + f"  [INST]  {turn}  [/INST]  "

		# query Together API 
		#
		res = requests.post(endpoint, json={
		    "model": "togethercomputer/llama-2-70b-chat",
		    "max_tokens": 1024,
		    "prompt": prompt,
		    "request_type": "language-model-inference",
		    "temperature": 0.7,
		    "top_p": 0.7,
		    "top_k": 50,
		    "repetition_penalty": 1,
		    "stop": [
		        "[INST]"
		    ],
		    "safety_model": "",
		    "repetitive_penalty": 1
		}, headers={
		    "Authorization": "Bearer " + APIKEY,
		})

		# parse out the response
		# 
		try:
			response = res.json()["output"]["choices"][0]["text"]
		except:
			failed = 1
			print(res.__repr__())
			break

		# append respond to the conversation
		#
		prompt = prompt + response

	# if all queries succeed, insert the result to DB
	#   (also print it out)
	#
	if failed == 0:
		cur.execute(f"INSERT INTO results VALUES (?, ?, ?);", (key, turns.__repr__(), prompt))
		con.commit()
		print(prompt)
		print("----------------------------")
	else:
		print("## Failed!!", prompt)
		print("----------------------------")

# Dump all result out
res = cur.execute(f"SELECT results FROM results;")
for fetched in res.fetchall():
	text = fetched[0]

  # Some basic cleaning and stripping
	text = text.replace("[INST]", "  [INST]")
	for i in range(0, 20):
		if f"[INST]  {i} / {i}-" in text:
			text = text.replace(f"INST]  {i} / {i}-", "INST]  ")
		if f"[INST]  {i} / {i}" in text:
			text = text.replace(f"INST]  {i} / {i}", "INST]  ")
	text = text.strip()

  out_file.write(json.dumps({"text": text}) + "\n")
out_file.close()

