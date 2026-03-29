from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
import discord
from discord import app_commands

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_root, ".env"))
sys.path.insert(0, _root)

from agent.utils.config import get_config
from discord_bot.commands import profile as profile_cmd
from discord_bot.commands import bot as bot_cmd


class YourFriendBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        profile_cmd.register(self.tree)
        bot_cmd.register(self.tree)
        await self.tree.sync()

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user} (id: {self.user.id})")


def main() -> None:
    config = get_config()
    if not config.Discord_Bot_Token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set in environment variables.")
    bot = YourFriendBot()
    bot.run(config.Discord_Bot_Token)


if __name__ == "__main__":
    main()
