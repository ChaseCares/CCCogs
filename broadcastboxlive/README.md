# BroadcastBoxLive

Name `broadcastboxlive`
Short name `[p]bbl`.
Run `[p]help bbl` for help.

[Broadcast Box](https://github.com/Glimesh/broadcast-box) lets you broadcast to others in sub-second time. This cog is designed to monitor the status page have a Broadcast Box instance and show who is currently streaming.

![Broadcast Box Live embed example](./img/broadcastboxlive-embed.png)

To install the BroadcastBoxLive cog, run:

```console
[p]cog install RedBotCogs broadcastboxlive
```

Now that it's installed we need to load it with:

```console
[p]load broadcastboxlive
```

Everything is installed and ready to use.

## Usage

Run `[p]bbl status` to get who is currently streaming to Broadcast Box.

`[p]bbl seturl <url>` to check for updates on a custom server.

`[p]bbl addchannel` to subscribe the current channel to receive regular updates or `[p]bbl addchannel <channel id>` to subscribe a specific channel.

`[p]bbl rmchannel` to unsubscribe the current channel or `[p]bbl rmchannel <channel id>` to unsubscribe a specific channel.

[Unload instructions](../README.md#unload-cog-and-remove-repository-instructions)
