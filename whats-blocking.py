#!/usr/bin/env python3

import argparse
import json
import os
import time
from urllib.request import urlopen, Request

URL_BASE = "https://api.nextdns.io/profiles/{}"
URL_TMPL = URL_BASE + "/logs?status=blocked&limit=1000"


def get_test_data(profile_id: str = ""):
    return [
        dict(reasons=[dict(id="a")]),
        dict(reasons=[dict(id="b")]),
        dict(reasons=[dict(id="c"), dict(id="d")]),
    ]


def get_api_data(api_key: str, profile_id: str, save: bool = False):
    url = URL_TMPL.format(profile_id)

    # Requests are blocked (403) when the default urllib user-agent is sent (WTF?)
    print("📡 Downloading logs …")
    resp = urlopen(
        Request(url, headers={"X-Api-Key": api_key, "User-Agent": "Phi/1.618"})
    )

    data = json.loads(resp.read())["data"]

    if save:
        fname = "{}-{}.json".format(profile_id, time.time())
        with open(fname, "w") as fo:
            json.dump(data, fo)
            print("💾 Wrote {}".format(fname))
    return data


def get_file_data(filename: str):
    with open(filename, "r") as fi:
        print("💾 Loading JSON from {}".format(filename))
        return json.load(fi)


def main(args: argparse.Namespace, config: dict[str, str]):
    solos: dict[str, set[str]] = {}
    combos: dict[tuple[str, ...], set[str]] = {}

    if args.profile:
        api_key = os.environ.get("NEXTDNS_API_KEY", config["api_key"])
        profile_id = config["profiles"][args.profile]
        data = get_api_data(api_key, profile_id, args.save)
    elif args.file:
        data = get_file_data(args.file)
    else:
        print("No profile or file specified!")  # shouldn't get here
        raise SystemExit(1)

    print("✅ Found {} entries".format(len(data)))

    # find entries appearnig by themselves
    for entry in data:
        if len(entry["reasons"]) == 1:
            bl_id = entry["reasons"][0]["id"]
            solos.setdefault(bl_id, set())
            solos[bl_id].add(entry["domain"])
            continue

    # find entries only appearing with other entries that aren't unique
    for entry in data:
        bl_ids = set([r["id"] for r in entry["reasons"]])
        if solos.keys() & bl_ids:  # keep going if any of these blocklists are in solos
            continue
        k = tuple(sorted(bl_ids))
        combos.setdefault(k, set())
        combos[k].add(entry["domain"])

    print("\n#\n# Blocklists appearing by themselves\n#\n")
    print("domains\tid")
    print("--     \t--")
    for bl_id in sorted(solos):
        print("{}\t{}\n\t{}".format(len(solos[bl_id]), bl_id, solos[bl_id]))

    if combos:
        print("\n#\n# Blocklists found only in combos\n#\n")
        print("domains\tid")
        print("--     \t--")
        for bl_ids in combos:
            print("{}\t{}\n\t{}".format(len(combos[bl_ids]), bl_ids, combos[bl_ids]))


def get_config(fname: str):
    with open(fname, "r") as fi:
        return json.load(fi)


def get_args():
    parser = argparse.ArgumentParser(description="Find blocklists in use.")
    parser.add_argument("-c", "--config", default="config.json")
    parser.add_argument(
        "-s", "--save", help="Save downloaded data", action="store_true"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--profile")
    group.add_argument("-f", "--file")

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    main(args, get_config(args.config))
