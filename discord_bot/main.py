from __future__ import annotations

import asyncio
import os
import sys
import uuid

import discord
from discord import app_commands
from dotenv import load_dotenv

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_root, ".env"))
sys.path.insert(0, _root)

from agent.main import analyze_message
from agent.storage import supa_db_manager
from agent.utils.config import get_config
from discord_bot.commands import bot as bot_cmd
from discord_bot.commands import profile as profile_cmd

_DISCORD_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _discord_uuid(discord_id: str) -> str:
    """Return a deterministic UUID string derived from a Discord snowflake ID."""
    return str(uuid.uuid5(_DISCORD_NS, f"discord:{discord_id}"))


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

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        # Only handle direct messages
        if message.guild is not None:
            return

        discord_id = str(message.author.id)
        user_uuid = _discord_uuid(discord_id)

        bot_profile = await asyncio.to_thread(
            supa_db_manager.get_bot_profile_by_user, user_uuid
        )

        if bot_profile:
            message = analyze_message(
                bot_profile["bot_id"], bot_profile["user_id"], message.content
            )
            await message.channel.send(message)
        # else:
        #     print(
        #         f"[DM] No BotProfile found for discord_id={discord_id} (user_uuid={user_uuid})"
        #     )


def main() -> None:
    config = get_config()
    if not config.Discord_Bot_Token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set in environment variables.")
    bot = YourFriendBot()
    bot.run(config.Discord_Bot_Token)


if __name__ == "__main__":
    main()
