# NextDNS Tools

This is where I'm gonna drop any scripts I make for managing NextDNS. Mostly, it's trying to make up for the lack of tooling provided by the web UI.

## `whats-blocking.py`

It's common to over-subscribe to blocklists, but it quickly turns into diminishing returns as there's a lot of overlap in what they block. This tool tries to glean which blocklists are actually needed.

It finds all the lists that are the only one to block a domain and then finds anything that only shows up in combinations with others. The idea is to run this over some period of time (days, weeks, months, up to you) and see what lists are doing the work. You can then, in theory, unsubscribe from everything else.

For lists only showing up in combination with others, pick the one that's most actively updated.

Lists come and go so you'll want to add new things that become available over time and then use the script to see where things stand.

## API Key

The API key can be specific via the `NEXTDNS_API_KEY` environment variable or added to the config file.

## Config file format

Create `config.json` (or use a different name and specify `-c filename`) that looks like:

```json
{
	"api_key": "4cdd946e6d2404c35bedfbc376cda6123230df20",
	"profiles": {
		"nice-name1": "d557f3",
		"easy-name2": "72a674"
	}
}
```

The profile names can be anything you want, they don't need to match the names on NextDNS. What's important is the hexadecmial profile id. The name is used with `-p` to specify the profile you want.