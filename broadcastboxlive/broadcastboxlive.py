# -*- coding: utf-8 -*-
import time
import aiohttp
import discord
import logging

# Remove Union when minimum python version is > 3.10
from discord.ext import tasks
from typing import Union, Optional, Dict, Any
from redbot.core import Config, commands, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import success, error, info

__all__ = ["UNIQUE_ID", "BroadcastBoxLive"]

log = logging.getLogger("red.redbotcogs.broadcastboxlive")
_ = Translator("BroadcastBoxLive", __file__)

UNIQUE_ID = 0x1549B7C6E4C7575

BB_URL = "https://b.siobud.com/api/status"
EMBED_TITLE = "Live on Broadcast Box Now"


@cog_i18n(_)
class BroadcastBoxLive(commands.Cog):
    """A simple cog to post lave broadcast box streams"""

    async def _manage_channel(self, ctx: commands.Context, action: str, channel: Optional[int]):
        if ctx.author.bot:
            return

        async with ctx.typing():
            if ctx.guild is None:
                await ctx.send(info(_("This command is only available in server/guild context.")))
                return

            async with self.conf.guild(ctx.guild).channels() as channels:
                try:
                    target_channel = ctx.channel if channel is None else channel
                    target_channel = await commands.TextChannelConverter().convert(
                        ctx, str(target_channel)
                    )
                except commands.ChannelNotFound:
                    log.error(f"{channel} channel not found")
                    await ctx.send(
                        error(_("{channel} channel doesn't exist.".format(channel=channel)))
                    )
                    return

                if action == "add":
                    if target_channel.id in channels:
                        await ctx.send(
                            info(
                                _("{channel} is already receiving stream updates.").format(
                                    channel=target_channel.mention
                                )
                            )
                        )
                    else:
                        try:
                            await self._publish_update(ctx.guild, target_channel.id)
                        except discord.errors.Forbidden:
                            await ctx.send(
                                error(
                                    _("I don't have permission to send messages and/or embeds to that channel.")
                                )
                            )
                            return
                        else:
                            channels.append(target_channel.id)
                            await ctx.send(
                                success(
                                    _(
                                        "Added {channel} to the list of channels receiving stream updates."
                                        " To remove this channel, use `{prefix}bbl remove {channel}`."
                                    ).format(channel=target_channel.mention, prefix=ctx.prefix)
                                )
                            )

                elif action == "remove":
                    if target_channel.id in channels:
                        channels.remove(target_channel.id)
                        await ctx.send(
                            success(
                                _(
                                    "Removed {channel} from the list of channels receiving stream updates."
                                ).format(channel=target_channel.mention)
                            )
                        )
                    else:
                        await ctx.send(
                            info(
                                _("{channel} is not receiving stream updates.").format(
                                    channel=target_channel.mention
                                )
                            )
                        )

    async def _get_current_status(self, guild: int, url: str) -> Union[int, None]:
        if guild is None:
            return None

        url_bb_status = await self.conf.url_bb_status()
        last_checked = url_bb_status.get(url, {}).get("last_checked", 0)
        interval = await self.conf.guild(guild).interval()

        if time.time() - last_checked < interval:
            return None

        async with aiohttp.ClientSession() as client:
            try:
                async with client.get(url) as resp:
                    resp_status = resp.status
                    if resp_status == 200:
                        data = await resp.json()
                        url_bb_status[url] = {
                            "data": data,
                            "resp_status": resp_status,
                            "last_checked": int(time.time()),
                        }
                        await self.conf.url_bb_status.set(url_bb_status)
                    else:
                        log.error(f"Error getting json. Status code: {resp_status}")
                    return resp_status
            except aiohttp.ClientError as e:
                log.error(f"Error fetching URL: {url}. Exception: {e}")
                return None

    async def _format_embed(
        self, url: str, data: Dict[str, Any], conn_quality: int
    ) -> discord.Embed:
        server = "Official" if url == BB_URL else "Custom"

        connection_status = "✅" if conn_quality == 200 else f"{conn_quality} ‼️"
        connection_color = 0x00FF00 if conn_quality == 200 else 0xFF0000

        embed = discord.Embed(title=EMBED_TITLE, color=connection_color)
        embed.description = f"Connection: {connection_status}\nServer: {server}"

        streams = 0
        for stream in data:
            audio_packets_received = stream.get("audioPacketsReceived", 0)
            video_streams = stream.get("videoStreams", [])

            # Filter out non streamers
            if audio_packets_received == 0 and not video_streams:
                continue

            stream_key = stream["streamKey"].replace("Bearer ", "")
            sessions = len(stream.get("whepSessions", []))
            first_seen = stream.get("firstSeenEpoch", time.time())
            live_for_epoch = int(time.time()) - first_seen
            hours, remainder = divmod(live_for_epoch, 3600)
            minutes, seconds = divmod(remainder, 60)

            stream_url = url.replace("api/status", stream_key)
            embed.add_field(
                name=stream_key,
                value=f"[URL]({stream_url}), Sessions: {sessions}, Live for: {hours:0>2d}:{minutes:0>2d}:{seconds:0>2d}",
                inline=False,
            )
            streams += 1

        if not streams:
            embed.add_field(name="No streams online", value="", inline=False)

        return embed

    async def _publish_update(self, guild: discord.Guild, channel: int):
        url = await self.conf.guild(guild).url()
        url_bb_status = await self.conf.url_bb_status()

        if url not in url_bb_status:
            resp = await self._get_current_status(guild, url)
            log.warning(f"From get_current_status resp: {resp}")
            if resp is None:
                return

        bb_data = url_bb_status.get(url, {}).get("data")
        bb_resp_status = url_bb_status.get(url, {}).get("resp_status")

        embed = await self._format_embed(url, bb_data, bb_resp_status)
        message_id = await self.conf.guild(guild).message()

        update_message = False
        async for message in self.bot.get_channel(channel).history(limit=5):
            if message.author == self.bot.user and message.embeds:
                if message.embeds[0].title == EMBED_TITLE:
                    update_message = True
                    break

        channel = self.bot.get_channel(channel)

        if message_id and update_message:
            try:
                message = await channel.fetch_message(message_id)
            except discord.errors.NotFound:
                message = await channel.send(embed=embed)
                await self.conf.guild(guild).message.set(message.id)
            else:
                await message.edit(embed=embed)
        else:
            message = await channel.send(embed=embed)
            await self.conf.guild(guild).message.set(message.id)

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_guild(channels=[], message=None, interval=60, url=BB_URL)
        self.conf.register_global(url_bb_status={})
        self.background_check_for_update.start()

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> Dict[str, Any]:
        """Nothing to get."""
        return {}

    async def init_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=60)
    async def background_check_for_update(self):
        for guild in self.bot.guilds:
            channels = await self.conf.guild(guild).channels()
            if channels.__len__() == 0:
                continue

            url = await self.conf.guild(guild).url()
            await self._get_current_status(guild, url)

            for channel in channels:
                await self._publish_update(guild, channel)

    @background_check_for_update.before_loop
    async def wait_for_red(self):
        await self.bot.wait_until_red_ready()

    async def cog_unload(self):
        self.background_check_for_update.cancel()

    @commands.group()
    async def bbl(self, ctx: commands.Context):
        """A simple cog to post lave broadcast box streams."""

    @checks.admin_or_permissions(manage_guild=True)
    @bbl.command(usage="Optional[interval]")
    async def interval(self, ctx: commands.Context, interval: Optional[int]):
        """
        Set the interval in seconds to check for updates.

        Default is 60 seconds
        Please be nice to the Broadcast Box server ❤️
        """

        if ctx.message.author.bot:
            return

        async with ctx.channel.typing():
            if ctx.guild is None:
                await ctx.send(info(_("This command is only available in server/guild context.")))
                return

            if interval is None:
                interval = await self.conf.guild(ctx.guild).interval()
                await ctx.send(
                    info(_("Currently checking every {number} seconds.").format(number=interval))
                )
                return
            elif interval < 20:
                await ctx.send(error(_("You cannot set the interval to less than 20 seconds.")))
                return

            await self.conf.guild(ctx.guild).interval.set(interval)
            self.background_check_for_update.change_interval(seconds=interval)
            await ctx.send(
                success(
                    _("Now checking every {number} seconds for a new streams.").format(
                        number=interval
                    )
                )
            )

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @bbl.command(name="addchannel", aliases=["add"], usage="Optional[channel]")
    async def addChannel(self, ctx: commands.Context, channel: Optional[int]):
        """
        Adds the current or a given channel to receive regular FFFs.

        - If no channel is given, the current channel will be added.
        - `<channel>`: If a channel is given, that channel is added.
        """

        await self._manage_channel(ctx, "add", channel)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @bbl.command(name="rmchannel", aliases=["remove"], usage="Optional[channel]")
    async def removeChannel(self, ctx: commands.Context, channel: Optional[int]):
        """
        Removes the current or a given channel from receiving regular FFFs.

        - If no channel is given, the current channel is removed.
        - `<channel>`: If a channel is given, that channel is removed.
        """

        await self._manage_channel(ctx, "remove", channel)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @bbl.command(name="seturl")
    async def seturl(self, ctx: commands.Context, url: str):
        """
        Set the Broadcast Box URL.

        This will set the URL for the Broadcast Box.

        Acceptable URL forms:
        - https://b.siobud.com/api/status
        - http://siobud.com/api/status
        - http://custom_domain.com:8080/api/status
        - http://192.168.1.1:3000/api/status
        """

        if ctx.message.author.bot:
            return

        if not url.startswith("http"):
            await ctx.send(
                error(
                    _(
                        "Invalid URL. Must start with http:// or https://. (e.g. https://b.siobud.com/api/status)"
                    )
                )
            )
            return

        if url.endswith("/api/status"):
            await ctx.send(success(_("Broadcast Box URL set to {url}").format(url=url)))
        else:
            await ctx.send(
                error(
                    _(
                        "Invalid URL. Please use a valid Broadcast Box URL. (e.g. https://b.siobud.com/api/status)"
                    )
                )
            )
            return

        await self.conf.guild(ctx.guild).url.set(url)

    @commands.guild_only()
    @bbl.command(name="status")
    async def status(self, ctx: commands.Context):
        """
        Get the current status of the Broadcast Box.

        This will show the current status of the Broadcast Box.
        """
        if ctx.message.author.bot:
            return

        if await self._get_current_status(ctx.guild, await self.conf.guild(ctx.guild).url()):
            await self._publish_update(ctx.guild, ctx.channel.id)
