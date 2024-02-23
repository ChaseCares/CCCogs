# FactorioCogFriday

Name `factoriocogfriday`
Short name `[p]fcf`.
Run `[p]help fcf` for help.

[Factorio](https://www.factorio.com/) is a construction and management simulation game, that publishes regular blogs called Factorio Friday Facts. This cog checks for an update every 6 hours (as to not be too intrusive) and since a notification when a new FFF is published. Only does one network request to factorio.com per Red-DiscordBot instance, regardless of how many guilds the bot is in.

## Features

- Add a channel to receive regular updates when new FFFs are released
- Issue a command to get a link to a specific FFF

To install the FactorioCogFriday cog, run:

```console
[p]cog install RedBotCogs factoriocogfriday
```

Now that it's installed we need to load it with:

```console
[p]load factoriocogfriday
```

Everything is installed and ready to use.

## Usage

Run `[p]fcf fff` to receive the latest FFF or `[p]fcf fff <number>` to get a link to a specific FFF.

`[p]fcf addchannel` to subscribe the current channel to receive regular updates or `[p]fcf addchannel <channel id>` to subscribe a specific channel.

`[p]fcf rmchannel` to unsubscribe the current channel or `[p]fcf rmchannel <channel id>` to unsubscribe a specific channel.

[Unload instructions](../README.md#unload-cog-and-remove-repository-instructions)
