
import datasets
import requests
import sqlite3
import sys

endpoint = 'https://api.together.xyz/inference'
APIKEY = "Put your Together API Key here

# A local database to store the result of all queries 
#
# Schema: results(instruction text, response text)
#   - instruction: input instruction
#   - response: response from the model
#
import sqlite3
con = sqlite3.connect("evaldb.db")
cur = con.cursor()

# Load Alpaca_eval evaluation set
#
eval_set = datasets.load_dataset("tatsu-lab/alpaca_eval", "alpaca_eval")["eval"]

# Output results to `sys.argv[1]`
#
outfile = open(sys.argv[1])

# for each example
#
for example in eval_set:

    # Instruction
    instruction = example["instruction"]

    # Check if the results are cached
    #
    res = cur.execute("SELECT results FROM results WHERE instruction=?;", (instruction,))
    fetched = res.fetchone()
    if fetched != None:
        continue

    # Query Together API
    #
    res = requests.post(endpoint, json={
        "model": "together/llama-2-7b-32k-chat",
        "max_tokens": 1500,
        "prompt": f"[INST] {instruction} [/INST]",
        "request_type": "language-model-inference",
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "repetition_penalty": 1.1,
        "stop": [
            "[INST]"
        ],
    }, headers={
        "Authorization": "Bearer " + APIKEY,
    })

    try:
        response = res.json()["output"]["choices"][0]["text"]

        print("------------")
        print(instruction)
        print("---")
        print(response)
        print("------------")

        # Insert into the DB
        #
        cur.execute(f"INSERT INTO results VALUES (?, ?);", (instruction, response))
        con.commit()

    except:
        print("-------")
        print(res.__repr__())
        break

# Python Object storing results  
#
rs = []

# Get all instruction/output pairs
#
res = cur.execute(f"SELECT instruction, results FROM results;")
for (instruction, results) in res.fetchall():
	results = results.strip()
	rs.append({"instruction": instruction,
				"output": results})
  
outfile.write(json.dumps(rs))
outfile.close()
