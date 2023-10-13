# -*- coding: utf-8 -*-
import re
import bs4
import time
import aiohttp
import discord
import feedparser

from typing import Tuple
from discord.ext import tasks

from redbot.core import Config, commands, checks

__all__ = ["UNIQUE_ID", "FactorioCogFriday"]

UNIQUE_ID = 0x10692DF0DC6C388

# RSS feed
FFF_RSS = "https://www.factorio.com/blog/rss"

# https://github.com/arielbeje/uBot/blob/b270ad2143bdec59356389480d401bf6b8ef058b/cogs/factorio.py
fffEx = re.compile(r"Friday Facts #(\d*)")
fffnumEx = re.compile(r"<id>https://www\.factorio\.com/blog/post/fff-(\d*)</id>")


async def get_soup(url: str) -> Tuple[int, bs4.BeautifulSoup]:
    """
    Returns a list with the response code (as int) and a BeautifulSoup object of the URL
    """
    async with aiohttp.ClientSession() as client:
        async with client.get(url) as resp:
            status = resp.status
            r = await resp.text()
    return (status, bs4.BeautifulSoup(r, "html.parser"))


async def embed_fff_abridged(number: str) -> discord.Embed:
    """
    Returns a discord.Embed object derived from an fff number
    """
    link = f"https://factorio.com/blog/post/fff-{number}"
    response = await get_soup(link)
    if response[0] == 200:
        soup = response[1]
        titleList = soup.find_all("h2")
        em = discord.Embed(
            title=titleList[0].string.strip(), url=link, color=discord.Color.dark_green()
        )
        meta_tag = soup.find("meta", property="og:description")
        if meta_tag:
            og_description = meta_tag.get("content")
            em.add_field(name="Description", value=og_description)

    else:
        em = discord.Embed(
            title="Error", description=f"Couldn't find FFF #{number}.", color=discord.Color.red()
        )
    return em


def checkTimeout(last_checked, timeout):
    if last_checked and int(time.time()) - last_checked < timeout:
        return False
    return True


class FactorioCogFriday(commands.Cog):
    """A simple cog to post FFFs when they're available."""

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_guild(fff_info={}, channels=[])
        self.conf.register_global(latest_fff=None, last_checked=None, timeout=600)
        self.background_check_for_update.start()

    async def init_loop(self):
        await self.bot.wait_until_ready()

    async def cog_unload(self):
        self.background_check_for_update.cancel()

    @tasks.loop(hours=6)
    async def background_check_for_update(self):
        await self._get_latest_fff()

        for guild in self.bot.guilds:
            channel = await self.conf.guild(guild).channels()
            for channel in channel:
                await self._check_for_update(guild, channel)

    @background_check_for_update.before_loop
    async def wait_for_red(self):
        await self.bot.wait_until_red_ready()

    async def _check_for_update(self, guild: discord.Guild, channel: int):
        fff_info = await self.conf.guild(guild).fff_info()
        fff_sent_to_channel = fff_info.get(str(channel))
        latest_fff = await self.conf.latest_fff()

        if not fff_sent_to_channel or fff_sent_to_channel < latest_fff:
            em = await embed_fff_abridged(latest_fff)
            await guild.get_channel(channel).send(embed=em)
            fff_info[channel] = latest_fff

        await self.conf.guild(guild).fff_info.set(fff_info)

    async def _get_latest_fff(self):
        last_checked = await self.conf.last_checked()
        timeout = await self.conf.timeout()
        if checkTimeout(last_checked, timeout):
            async with aiohttp.ClientSession() as client:
                async with client.get(FFF_RSS) as resp:
                    status = resp.status
                    if status != 200:
                        # TODO log error
                        return

                    text = await resp.text()

            await self.conf.latest_fff.set(int(re.search(fffnumEx, text).group(1)))
            await self.conf.last_checked.set(int(time.time()))

    @commands.group()
    async def factorio_cog_friday(self, ctx: commands.Context):
        """A simple cog to post FFFs when they're available."""

    @factorio_cog_friday.command()
    async def fff(self, ctx: commands.Context, number: str = None):  # type: ignore
        """
        Links the latest fff or the specific fff if a number is provided.
        """
        if number is not None:
            try:
                em = await embed_fff_abridged(number)  # type: ignore
            except ValueError:
                em = discord.Embed(
                    title="Error",
                    description="To use the command, you need to input a number.",
                    color=discord.Color.red(),
                )
        else:
            async with ctx.channel.typing():
                async with aiohttp.ClientSession() as client:
                    async with client.get(FFF_RSS) as resp:
                        status = resp.status
                        r = await resp.text()
                if status == 200:
                    rss = feedparser.parse(r)
                    i = 0
                    entry = rss.entries[i]
                    while "friday facts" not in entry.title.lower():
                        i += 1
                        entry = rss.entries[i]
                    em = await embed_fff_abridged(fffEx.search(entry.title).group(1))  # type: ignore
                else:
                    em = discord.Embed(
                        title="Error",
                        description="Couldn't find the latest FFF.",
                        color=discord.Color.red(),
                    )

        await ctx.send(embed=em)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @factorio_cog_friday.command(name="add_channel")
    async def addChannel(self, ctx: commands.Context):
        """
        Adds the current channel to receive regular FFFs.
        """
        async with self.conf.guild(ctx.guild).channels() as channels:
            if ctx.channel.id in channels:
                await ctx.send("This channel is already receiving FFFs.")
            else:
                channels.append(ctx.channel.id)
                await ctx.send("Added this channel to the list of channels receiving FFFs.")

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @factorio_cog_friday.command(name="remove_channel")
    async def removeChannel(self, ctx: commands.Context):
        """
        Removes the current channel from receiving regular FFFs.
        """
        async with self.conf.guild(ctx.guild).channels() as channels:
            if ctx.channel.id in channels:
                channels.remove(ctx.channel.id)
                await ctx.send("Removed this channel from the list of channels receiving FFFs.")
            else:
                await ctx.send("This channel is not receiving FFFs.")
