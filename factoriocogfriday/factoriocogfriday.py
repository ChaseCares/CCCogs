# -*- coding: utf-8 -*-
import re
import time
import aiohttp
import discord

# Remove when minimum python version is > 3.10
from typing import Union, Optional
from discord.ext import tasks
from redbot.core import Config, commands, checks

__all__ = ["UNIQUE_ID", "FactorioCogFriday"]

UNIQUE_ID = 0x10692DF0DC6C388

FFF_RSS = "https://www.factorio.com/blog/rss"

fffnumREPat = re.compile(r"<id>https://www\.factorio\.com/blog/post/fff-(\d*)</id>")


class FactorioCogFriday(commands.Cog):
    """A simple cog to post FFFs"""

    def _checkTimeout(self, last_checked, timeout) -> bool:
        if last_checked and int(time.time()) - last_checked < timeout:
            return False
        return True

    async def _check_for_update(self, guild: discord.Guild, channel: int):
        fff_info = await self.conf.guild(guild).fff_info()
        fff_sent_to_channel = fff_info.get(str(channel))
        latest_fff = await self.conf.latest_fff()

        if not fff_sent_to_channel or fff_sent_to_channel < latest_fff:
            await self.bot.get_channel(channel).send(
                f"New FFF! https://factorio.com/blog/post/fff-{latest_fff}"
            )
            fff_info[channel] = latest_fff

        await self.conf.guild(guild).fff_info.set(fff_info)

    async def _get_latest_fff_number(self) -> Union[int, None]:
        async with aiohttp.ClientSession() as client:
            async with client.get(FFF_RSS) as resp:
                status = resp.status
                if status == 200:
                    text = await resp.text()
                    found_fff_num = re.search(fffnumREPat, text)
                    if found_fff_num:
                        return int(found_fff_num.group(1))
        return None

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_guild(fff_info={}, channels=[])
        self.conf.register_global(latest_fff=None, last_checked=None, timeout=600)
        self.background_check_for_update.start()

    async def init_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=6)
    async def background_check_for_update(self):
        last_checked = await self.conf.last_checked()
        timeout = await self.conf.timeout()
        if self._checkTimeout(last_checked, timeout):
            fff_num = await self._get_latest_fff_number()
            if fff_num:
                await self.conf.latest_fff.set(fff_num)
                await self.conf.last_checked.set(int(time.time()))

        for guild in self.bot.guilds:
            channel = await self.conf.guild(guild).channels()
            for channel in channel:
                await self._check_for_update(guild, channel)

    @background_check_for_update.before_loop
    async def wait_for_red(self):
        await self.bot.wait_until_red_ready()

    async def cog_unload(self):
        self.background_check_for_update.cancel()

    @commands.group()
    async def fcf(self, ctx: commands.Context):
        """A simple cog to post FFFs when they're available."""

    @fcf.command()
    async def fff(self, ctx: commands.Context, number: Optional[int]):
        """
        Links the latest fff or the specific FFF if a number is provided.
        """
        if number is not None:
            await ctx.send(f"https://factorio.com/blog/post/fff-{number}")
        else:
            async with ctx.channel.typing():
                fff_num = await self._get_latest_fff_number()
                if fff_num:
                    await ctx.send(f"https://factorio.com/blog/post/fff-{fff_num}")
                else:
                    await ctx.send("Error finding FFF number.")

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @fcf.command(name="addchannel")
    async def addChannel(self, ctx: commands.Context, channel: Optional[int]):
        """
        Adds the current or a given channel to receive regular FFFs.
        """
        if ctx.guild is not None:
            if channel is None:
                async with self.conf.guild(ctx.guild).channels() as channels:
                    if ctx.channel.id in channels:
                        await ctx.send("This channel is already receiving FFFs.")
                    else:
                        channels.append(ctx.channel.id)
                        await ctx.send(
                            f"Added this channel to the list of channels receiving FFFs.\nTo remove this channel, use `{ctx.prefix}fcf rmchannel`."
                        )
            else:
                try:
                    text_channel = await commands.TextChannelConverter().convert(
                        ctx, str(channel)
                    )
                except commands.ChannelNotFound:
                    await ctx.send("That channel doesn't exist.")
                    return
                async with self.conf.guild(ctx.guild).channels() as channels:
                    if text_channel.id in channels:
                        await ctx.send("That channel is already receiving FFFs.")
                    else:
                        try:
                            await self._check_for_update(ctx.guild, text_channel.id)
                        except discord.errors.Forbidden:
                            await ctx.send(
                                "I don't have permission to send messages to that channel."
                            )
                            return
                        except Exception as e:
                            await ctx.send(f"Error: {e}")
                            return
                        else:
                            channels.append(text_channel.id)
                            await ctx.send(
                                f"Added {text_channel.mention} to the list of channels receiving FFFs.\nTo remove this channel, use `{ctx.prefix}fcf rmchannel {text_channel.mention}`."
                            )

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @fcf.command(name="rmchannel")
    async def removeChannel(self, ctx: commands.Context, channel: Optional[int]):
        """
        Removes the current or a given channel from receiving regular FFFs.
        """
        if ctx.guild is not None:
            if channel is None:
                async with self.conf.guild(ctx.guild).channels() as channels:
                    if ctx.channel.id in channels:
                        channels.remove(ctx.channel.id)
                        await ctx.send(
                            "Removed this channel from the list of channels receiving FFFs."
                        )
                    else:
                        await ctx.send("This channel is not receiving FFFs.")
            else:
                try:
                    text_channel = await commands.TextChannelConverter().convert(
                        ctx, str(channel)
                    )
                except commands.ChannelNotFound:
                    await ctx.send("That channel doesn't exist.")
                    return
                async with self.conf.guild(ctx.guild).channels() as channels:
                    if text_channel.id in channels:
                        channels.remove(text_channel.id)
                        await ctx.send(
                            f"Removed {text_channel.mention} from the list of channels receiving FFFs."
                        )
                    else:
                        await ctx.send(f"{text_channel.mention} is not receiving FFFs.")
