#!/usr/bin/env python3

import argparse
import base64
import json
import logging
import os
import pathlib
import re
import requests
import sys
import subprocess

logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")

def get_state_filename(args):
    state_fname = base64.b64encode(args.repo.encode('ascii')).decode('ascii') + ".json"
    return os.path.join(args.state_dir, state_fname)

def get_last_pr(state):
    if not os.path.exists(state):
        return 0

    with open(state) as f:
        try:
            data = json.load(f)
            return data["last_pr"] or 0
        except Exception as e:
            logging.warning(f"Error loading state file: {state}")
            return 0

def set_last_pr(state, pr):
    logging.debug(f"Setting last PR to {pr} in state file {state}")
    path = pathlib.Path(state)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(state, "w") as f:
        json.dump({"last_pr": pr}, f)

def get_api_endpoint(args):
    pattern = re.compile(r'^https://github.com/([^/]+)/([^/]+)')
    m = pattern.match(args.repo)
    if not m:
        raise Exception(f"Failed to parse Github repo URL: {args.repo}")
    org, repo = m.group(1), m.group(2)
    return f"https://api.github.com/repos/{org}/{repo}"

def get_api_token(args):
    if sys.platform == "darwin":
        srv = "github.com"
        logging.debug(f"Looking for Github token in keychain: service={srv}")
        p = subprocess.Popen(["security", "find-internet-password", "-s", "github.com", "-w"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate()
        if not out:
            raise Exception(f"Failed to retrieve API token from keychain: {err}")
        return out.strip()
    else:
        logging.debug(f"Looking for Github token in file: {args.token_file}")
        try:
            with open(args.token_file, "r") as f:
                token = f.read().strip()
                if not token:
                    raise Exception(f"token not found")
        except Exception as e:
            logging.fatal(f"Failed to read token from file: {args.token_file}: {e}")
            sys.exit(2)

def gh_api(args):
    api_ep = get_api_endpoint(args)
    token = get_api_token(args)

    def call(path, accept="application/vnd.github.v3+json"):
        r = requests.get(f"{api_ep}/{path}",
                         headers={
                             "Authorization": f"token {token}",
                             "Accept": accept,
                         })
        return r.json()

    return call

def get_prs(api, last_pr):
    prs = []
    for pr in api("pulls"):
        prnum = int(os.path.basename(pr["url"]))
        if prnum <= last_pr:
            continue

        url = pr["html_url"]
        prs.append((prnum, url))

    return prs

def get_pr_files(api, pr):
    return [ x["filename"] for x in api(f"pulls/{pr}/files") ]

def get_path_matcher(args):
    def matcher(path):
        for candidate in args.path:
            if path.startswith(candidate):
                logging.debug(f"Matched file: {path}")
                return True
        return False
    return matcher

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("repo", help="Github repo URL")
    parser.add_argument("path", nargs='+',
                        help="File/directory path to filter PRs")
    parser.add_argument("--state-dir", metavar="DIR",
                        default=os.path.expanduser("~/.gh-pr-notify"),
                        help="Directory to store state in")
    parser.add_argument("--token-file", metavar="FILE",
                        default=os.path.expanduser("~/.gh-token"),
                        help="Github token file (ignored on macOS)")
    parser.add_argument("--last-pr", type=int, metavar="NUM",
                        help="Override last PR to start checking from")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print verbose messages")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    state = get_state_filename(args)

    if args.last_pr:
        last_pr = args.last_pr
    else:
        last_pr = get_last_pr(state)

    api = gh_api(args)
    match = get_path_matcher(args)

    matched_prs = set()
    newest_pr = None
    for pr, url in get_prs(api, last_pr):
        logging.debug(f"Evaluating PR {url}")
        if not newest_pr:
            newest_pr = pr
        for file in get_pr_files(api, pr):
            if match(file):
                logging.info(f"PR {pr} includes file: {file}")
                matched_prs.add(url)
                break

    if matched_prs:
        logging.info(f"Found {len(matched_prs)} matching PRs")
        prs = sorted(matched_prs)
        print("-", "\n- ".join(sorted(matched_prs)))
    else:
        logging.info(f"No matching PRs newer than {last_pr}")

    if newest_pr and last_pr != newest_pr:
        set_last_pr(state, newest_pr)
