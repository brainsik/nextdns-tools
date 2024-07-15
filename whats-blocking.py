#!/usr/bin/env python3
# pyright: strict

import argparse
import json
import os
import time
from collections import defaultdict
from typing import Any, Callable, TypedDict
from urllib.request import urlopen, Request

URL_BASE = "https://api.nextdns.io/profiles/{}"
URL_TMPL = URL_BASE + "/logs?status=blocked&limit=1000"

NextDnsJson = Any
DomData = dict[str, set[str]]  # d[domain] = set[blists]
BlistData = dict[str, set[str]]  # d[blist_id] = set[domains]


class ConfigJson(TypedDict):
    api_key: str
    profiles: dict[str, str]


def json_to_domdata(jsondata: NextDnsJson) -> DomData:
    output: DomData = {}

    for entry in jsondata:
        blocklists = {r["id"] for r in entry["reasons"]}
        output[entry["domain"]] = blocklists

    return output


def domdata_to_blistdata(domdata: DomData) -> BlistData:
    blistdata: BlistData = defaultdict(set)

    for dom in domdata:
        for blist in domdata[dom]:
            blistdata[blist].add(dom)

    return blistdata


def get_api_data(api_key: str, profile_id: str, keep: bool = False) -> NextDnsJson:
    url = URL_TMPL.format(profile_id)

    # Requests are blocked (403) when the default urllib user-agent is sent (WTF?)
    print("📡 Downloading logs …")
    resp = urlopen(
        Request(url, headers={"X-Api-Key": api_key, "User-Agent": "Phi/1.618"})
    )
    data: NextDnsJson = json.loads(resp.read())

    if keep:
        fname = "{}-{}.log.json".format(profile_id, time.time())
        with open(fname, "w") as fo:
            json.dump(data, fo)
            print("💾 Wrote", fname)

    print("✅ Found {} log entries".format(len(data["data"])))
    return json_to_domdata(data["data"])


def get_file_data(fname: str) -> NextDnsJson:
    with open(fname, "r") as fi:
        print("💾 Loading JSON from", fname)
        data: NextDnsJson = json.load(fi)

    print("✅ Found {} log entries".format(len(data["data"])))
    return json_to_domdata(data["data"])


def update_domdata_store(name: str, domdata: DomData) -> DomData:
    fname = "{}.domdata.json".format(name)

    try:
        with open(fname, "r") as fi:
            jsondata = json.load(fi)
            for dom in jsondata:
                if dom in domdata:
                    if set(jsondata[dom]) != domdata[dom]:
                        print("⚠️  Blocklists used for {} changed".format(dom))
                        print("Was: {}".format(sorted(domdata[dom])))
                        print("Now: {}".format(sorted(set(jsondata[dom]))))
                else:
                    domdata[dom] = set(jsondata[dom])
    except FileNotFoundError:
        print("⚠️  No store found; will create", fname)

    with open(fname, "w") as fo:
        json_data: dict[str, list[str]] = {}
        for dom in domdata:
            json_data[dom] = list(domdata[dom])
        print("💾 Writing store", fname, "with", len(json_data), "domains")
        json.dump(json_data, fo, indent=2)

    return domdata


def print_domdata(domdata: DomData) -> None:
    print("⚙️  Processing {} domains".format(len(domdata)))

    solos: dict[str, set[str]] = defaultdict(set)  # blist -> doms
    combos: dict[tuple[str, ...], set[str]] = defaultdict(set)  # blists -> doms
    overlap: dict[str, list[int]] = defaultdict(list)  # blist -> redundancy

    for dom in domdata:
        for blist in domdata[dom]:
            overlap[blist].append(len(domdata[dom]))

        if len(domdata[dom]) == 1:
            blist = list(domdata[dom])[0]
            solos[blist].add(dom)

    # 2nd pass: find lists only appearing with other lists, but not the solos
    for dom in domdata:
        if solos.keys() & domdata[dom]:
            continue

        blists = tuple(sorted(domdata[dom]))
        combos[blists].add(dom)

    print("\n#\n# Blocklists appearing by themselves\n#\n")
    print("domains\tid")
    print("--     \t--")
    for blist in sorted(solos):
        print("{}\t{}\n\t{}".format(len(solos[blist]), blist, solos[blist]))

    if combos:
        print("\n#\n# Blocklists found only in combos\n#\n")
        print("domains\tid")
        print("--     \t--")
        for blists in combos:
            print("{}\t{}\n\t{}".format(len(combos[blists]), blists, combos[blists]))

    blistdata = domdata_to_blistdata(domdata)
    coverage_pct: Callable[[str], float]
    coverage_pct = lambda blist: len(blistdata[blist]) / len(domdata)
    print("\n#\n# Domain coverage ({} total)\n#\n".format(len(domdata)))
    for blist in sorted(blistdata, key=coverage_pct, reverse=True):
        print("{:4.1f}% {}".format(100 * coverage_pct(blist), blist))

    print("\n#\n# Redundancy histogram\n#\n")
    for blist in sorted(overlap):
        level_hist: dict[int, int] = defaultdict(int)
        for level in overlap[blist]:
            level_hist[level] += 1
        print(blist)

        for n in range(1, max(level_hist.keys()) + 1):
            level_str = "{:2d}".format(n)
            if n == 1:
                level_str = "🥇"
            if n == 2:
                level_str = "🥈"
            if n == 3:
                level_str = "🥉"

            print("{}: {}".format(level_str, "*" * level_hist.get(n, 0)))
        print()


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find blocklists in use.")
    parser.add_argument("-c", "--config", default="config.json")
    parser.add_argument(
        "-k", "--keep", help="Keep downloaded data in a file", action="store_true"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--profile")
    group.add_argument("-f", "--file")

    return parser.parse_args()


def get_config(fname: str) -> ConfigJson:
    with open(fname, "r") as fi:
        return json.load(fi)


def main():
    args = get_args()
    config = get_config(args.config)

    if args.profile:
        api_key = os.environ.get("NEXTDNS_API_KEY", config["api_key"])
        store_name = profile_id = config["profiles"][args.profile]
        domdata = get_api_data(api_key, profile_id, args.keep)
    elif args.file:
        store_name = args.file.partition("-")[0]
        domdata = get_file_data(args.file)
    else:
        print("No profile or file specified!")  # shouldn't get here
        raise SystemExit(1)

    domdata = update_domdata_store(store_name, domdata)
    print_domdata(domdata)


if __name__ == "__main__":
    main()
