# -*- coding: utf-8 -*-
import re
import time
import aiohttp
import discord
import logging

# Remove Union when minimum python version is > 3.10
from typing import Union, Optional, Dict, Any
from discord.ext import tasks
from redbot.core import Config, commands, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import success, error, info

__all__ = ["UNIQUE_ID", "FactorioCogFriday"]

log = logging.getLogger("red.redbotcogs.factoriocogfriday")
_ = Translator("FactorioCogFriday", __file__)

UNIQUE_ID = 0x10692DF0DC6C388

FFF_RSS = "https://www.factorio.com/blog/rss"
FFF_URL = "https://factorio.com/blog/post/fff-"

fffnumREPat = re.compile(r"<id>https://www\.factorio\.com/blog/post/fff-(\d*)</id>")


@cog_i18n(_)
class FactorioCogFriday(commands.Cog):
    """A simple cog to post FFFs"""

    def _check_timeout(self, last_checked, timeout) -> bool:
        if last_checked and int(time.time()) - last_checked < timeout:
            return False
        return True

    async def _check_for_update(self, guild: discord.Guild, channel: int):
        try:
            fff_info = await self.conf.guild(guild).fff_info()
            fff_sent_to_channel = fff_info.get(str(channel))
            latest_fff = await self.conf.latest_fff()

            if not fff_sent_to_channel or fff_sent_to_channel < latest_fff:
                target_channel = self.bot.get_channel(channel)
                if target_channel:
                    await target_channel.send(
                        _("New FFF! {fff_url}{number}").format(number=latest_fff, fff_url=FFF_URL)
                    )
                    fff_info[str(channel)] = latest_fff
                else:
                    log.error(f"Channel {channel} not found in guild {guild.name}.")
            else:
                log.debug(f"No new FFF to send to channel {channel} in guild {guild.name}.")

            await self.conf.guild(guild).fff_info.set(fff_info)
        except Exception as e:
            log.error(f"An error occurred during FFF update check: {e}")

    async def _get_latest_fff_number(self) -> Union[int, None]:
        try:
            async with aiohttp.ClientSession() as client:
                async with client.get(FFF_RSS) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        found_fff_num = re.search(fffnumREPat, text)
                        if found_fff_num:
                            return int(found_fff_num.group(1))
                        else:
                            log.error("Error finding FFF number.")
                    else:
                        log.error(f"Error getting latest FFF number. Status code: {resp.status}")
        except aiohttp.ClientError as e:
            log.error(f"Error during HTTP request: {e}")
        return None

    async def _manage_channel(
        self, ctx: commands.Context, action: str, channel: Optional[int] = None
    ):
        async with ctx.typing():
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
                                _("{channel} is already receiving FFFs updates.").format(
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
                                    _("I don't have permission to send messages to that channel.")
                                )
                            )
                        except Exception as e:
                            log.error(f"Error checking for update, error: {e}")
                            await ctx.send(error(_("Error: {error}").format(error=e)))
                        else:
                            channels.append(target_channel.id)
                            await ctx.send(
                                success(
                                    _(
                                        "Added {channel} to the list of channels receiving FFFs."
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
                                    "Removed {channel} from the list of channels receiving FFFs."
                                ).format(channel=target_channel.mention)
                            )
                        )
                    else:
                        await ctx.send(
                            info(
                                _("{channel} is not receiving FFFs updates.").format(
                                    channel=target_channel.mention
                                )
                            )
                        )

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_guild(fff_info={}, channels=[], interval=6)
        self.conf.register_global(latest_fff=None, last_checked=None, timeout=600)
        self.background_check_for_update.start()

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> Dict[str, Any]:
        """Nothing to get."""
        return {}

    async def init_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=6)
    async def background_check_for_update(self):
        last_checked = await self.conf.last_checked()
        timeout = await self.conf.timeout()

        if self._check_timeout(last_checked, timeout):
            fff_num = await self._get_latest_fff_number()
            if fff_num:
                await self.conf.latest_fff.set(fff_num)
                await self.conf.last_checked.set(int(time.time()))

        for guild in self.bot.guilds:
            channels = await self.conf.guild(guild).channels()
            for channel_id in channels:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await self._check_for_update(guild, channel)
                else:
                    log.error(f"Channel {channel_id} not found in guild {guild.name}.")

    @background_check_for_update.before_loop
    async def wait_for_red(self):
        await self.bot.wait_until_red_ready()

    async def cog_unload(self):
        self.background_check_for_update.cancel()

    @commands.group()
    async def fcf(self, ctx: commands.Context):
        """A simple cog to post FFFs when they're available."""

    @checks.admin_or_permissions()
    @commands.guild_only()
    @fcf.command(usage="Optional[interval]")
    async def interval(self, ctx: commands.Context, interval: Optional[float] = None):
        """
        Set the interval in hours at which to check for updates.

        Default is 6 hours
        Please be nice to the Factorio devs ❤️
        """

        if ctx.author.bot:
            return

        async with ctx.trigger_typing():
            if interval is None:
                interval = await self.conf.guild(ctx.guild).interval()
                await ctx.send(
                    info(_("Currently checking every {number} hours.").format(number=interval))
                )
                return
            elif interval < 1:
                await ctx.send(error(_("You cannot set the interval to less than 1 hour.")))
                return
            elif interval > 8760:
                await ctx.send(error(_("You cannot set the interval greater than 8760 hours.")))
                return

            await self.conf.guild(ctx.guild).interval.set(interval)
            self.background_check_for_update.change_interval(hours=interval)
            await ctx.send(
                success(
                    _("Now checking every {number} hours for a new FFF.").format(number=interval)
                )
            )

    @commands.cooldown(1, 5, commands.BucketType.guild)
    @fcf.command(usage="Optional[number]")
    async def fff(self, ctx: commands.Context, number: Optional[int] = None):
        """
        Links the latest FFF or the specific FFF if a number is provided.
        """

        async with ctx.trigger_typing():
            if number is not None:
                await ctx.send(info(_("{fff_url}{number}").format(fff_url=FFF_URL, number=number)))
            else:
                fff_num = await self._get_latest_fff_number()
                if fff_num:
                    await ctx.send(
                        info(_("{fff_url}{number}").format(fff_url=FFF_URL, number=fff_num))
                    )
                else:
                    await ctx.send(error(_("Error finding FFF number.")))

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @fcf.command(name="addchannel", aliases=["add"], usage="Optional[channel]")
    async def addChannel(self, ctx: commands.Context, channel: Optional[int] = None):
        """
        Adds the current or a given channel to receive regular FFFs.

        - If no channel is given, the current channel will be added.
        - `<channel>`: If a channel is given, that channel is added.
        """

        await self._manage_channel(ctx, "add", channel)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @fcf.command(name="rmchannel", aliases=["remove"], usage="Optional[channel]")
    async def removeChannel(self, ctx: commands.Context, channel: Optional[int] = None):
        """
        Removes the current or a given channel from receiving regular FFFs.

        - If no channel is given, the current channel is removed.
        - `<channel>`: If a channel is given, that channel is removed.
        """

        await self._manage_channel(ctx, "remove", channel)
