from redbot.core.utils import get_end_user_data_statement_or_raise

__red_end_user_data_statement__ = get_end_user_data_statement_or_raise(__file__)

from .broadcastboxlive import BroadcastBoxLive


async def setup(bot):
    await bot.add_cog(BroadcastBoxLive(bot))
