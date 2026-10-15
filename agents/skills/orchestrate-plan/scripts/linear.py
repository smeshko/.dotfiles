#!/usr/bin/env python3
"""Linear writes for the orchestrator, over GraphQL with LINEAR_API_KEY from the environment.

Usage:
  linear.py get <ISSUE>                    state and title: proves the route works
  linear.py tasks <ISSUE> <PLAN.md>        fill the issue's "## Tasks" section from the plan, move Backlog to Todo
  linear.py state <STATE> <ISSUE>...       set each issue's workflow state by name ("In Progress", "Done")
  linear.py create <TEAM-KEY> <file.json>  create Backlog issues from [{title, body, labels: [names]}]

Uses curl, because Python's urllib can fail certificate checks on machines whose
Python has no CA bundle. Never prints the key.
"""
import json
import os
import re
import subprocess
import sys


def gql(query, variables=None):
    out = subprocess.run(
        ["curl", "-s", "https://api.linear.app/graphql",
         "-H", "Authorization: " + os.environ["LINEAR_API_KEY"],
         "-H", "Content-Type: application/json", "--data-binary", "@-"],
        input=json.dumps({"query": query, "variables": variables or {}}),
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    if "errors" in data:
        sys.exit(json.dumps(data["errors"]))
    return data["data"]


ISSUE = "query($i:String!){issue(id:$i){id title description state{name} team{states{nodes{id name}}}}}"
UPDATE = "mutation($id:String!,$in:IssueUpdateInput!){issueUpdate(id:$id,input:$in){success}}"


def state_id(issue, name):
    return next(s["id"] for s in issue["team"]["states"]["nodes"] if s["name"] == name)


def get(ident):
    i = gql(ISSUE, {"i": ident})["issue"]
    print(ident, i["state"]["name"], "|", i["title"])


def tasks(ident, plan_path):
    plan = open(plan_path).read()
    section = plan.split("## Tasks", 1)[1].split("\n## ", 1)[0]
    lines = [re.sub(r"^- \[[ x]\]\s*", "", l).strip() for l in section.splitlines() if re.match(r"^- \[[ x]\]", l)]
    i = gql(ISSUE, {"i": ident})["issue"]
    body = "## Tasks\n\n" + "\n".join(f"* {t}" for t in lines) + "\n"
    desc = re.sub(r"## Tasks\n.*?(?=\n---|\n## |\Z)", lambda _: body, i["description"] or "", flags=re.S)
    if "## Tasks" not in desc:
        desc = desc.rstrip() + "\n\n" + body
    update = {"description": desc}
    if i["state"]["name"] == "Backlog":
        update["stateId"] = state_id(i, "Todo")
    gql(UPDATE, {"id": i["id"], "in": update})
    print(ident, len(lines), "tasks;", "moved to Todo" if "stateId" in update else "state kept " + i["state"]["name"])


def state(name, idents):
    for ident in idents:
        i = gql(ISSUE, {"i": ident})["issue"]
        if i["state"]["name"] != name:
            gql(UPDATE, {"id": i["id"], "in": {"stateId": state_id(i, name)}})
        print(ident, i["state"]["name"], "->", name)


def create(team_key, path):
    t = gql('query($k:String!){teams(filter:{key:{eq:$k}}){nodes{id states{nodes{id name}} labels(first:100){nodes{id name}}}}}',
            {"k": team_key})["teams"]["nodes"][0]
    backlog = next(s["id"] for s in t["states"]["nodes"] if s["name"] == "Backlog")
    labels = {l["name"]: l["id"] for l in t["labels"]["nodes"]}
    for l in gql("{issueLabels(first:100){nodes{id name team{id}}}}")["issueLabels"]["nodes"]:
        if l["team"] is None:
            labels.setdefault(l["name"], l["id"])
    for item in json.load(open(path)):
        missing = [n for n in item["labels"] if n not in labels]
        if missing:
            sys.exit(f"unknown labels {missing} for {item['title']!r}")
        r = gql("mutation($in:IssueCreateInput!){issueCreate(input:$in){issue{identifier}}}",
                {"in": {"teamId": t["id"], "title": item["title"], "description": item["body"],
                        "labelIds": [labels[n] for n in item["labels"]], "stateId": backlog}})
        print(r["issueCreate"]["issue"]["identifier"], item["title"])


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"get": lambda: get(*args), "tasks": lambda: tasks(*args),
     "state": lambda: state(args[0], args[1:]), "create": lambda: create(*args)}[cmd]()
