# Cogs for Red Discord Bot

Repository name RedBotCogs

## Installation Instructions

### Prerequisite

First make sure the downloader cog is loaded. To check, run:

```console
[p]cogs
```

`downloader` should be he in the loaded category. To check, run:

```console
[p]load downloader
```

For official information on the downloader cog, see [Red Discord Bot’s documentation](https://docs.discord.red/en/stable/cog_guides/downloader.htm)

Next add my repository with

```console
[p]repo add RedBotCogs https://github.com/ChaseCares/RedBotCogs
```

`RedBotCogs` will be the name of the repository

### FactorioCogFriday

Name `factoriocogfriday`
Short name `[p]fcf`.
Run `[p]help fcf` for help.

- Add a channel to receive regular updates when new FFFs are released
- Issue a command to get a link to a specific FFF

The cog checks for an update every 6 hours, as to be too intrusive. Only does one network request to factorio.com per server, what regardless of how many guilds the bot is in.

#### Features

To install the FactorioCogFriday cog, run:

```console
[p]cog install RedBotCogs factoriocogfriday
```

Now that it's installed we need to load it with:

```console
[p]load factoriocogfriday
```

Everything is installed and ready to use.

#### Usage

Run `[p]fcf fff` to receive the latest FFF or `[p]fcf fff <number>` to get a link to a specific FFF.

`[p]fcf addchannel` to subscribe the current channel to receive regular updates or `[p]fcf addchannel <channel id>` to subscribe a different channel.

`[p]fcf rmchannel` to unsubscribe the current channel or `[p]fcf rmchannel <channel id>` to unsubscribe a different channel.

## Unload Cog and Remove Repository Instructions

To unload a cog

```console
[p]unload <cogname>
```

To remove a repository

```console
[p]repo delete <reponame>
```
