"""Discord slash-command group:  /bot create"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

import discord
from discord import app_commands

from agent.managers.emotion_condition_manager import create_emotion_conditions
from agent.managers.rag_manager import index_backstory
from agent.managers.traits_manager import update_bot_traits
from agent.managers.worldview_manager import create_world_views_from_backstory

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)

from agent.storage import graph_db_manager, supa_db_manager

_DISCORD_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _discord_uuid(discord_id: str) -> str:
    return str(uuid.uuid5(_DISCORD_NS, f"discord:{discord_id}"))


# ── Modal ───────────────────────────────────────────────────


class BotCreateModal(discord.ui.Modal, title="สร้าง Bot ของคุณ"):
    def __init__(self, existing: dict | None = None) -> None:
        super().__init__()
        existing = existing or {}

        self.name_input = discord.ui.TextInput(
            label="Bot Name",
            placeholder="ชื่อ Bot",
            default=existing.get("name") or "",
            required=True,
            max_length=80,
        )
        self.backstory_input = discord.ui.TextInput(
            label="Backstory",
            style=discord.TextStyle.paragraph,
            placeholder="เรื่องราวพื้นหลังของ Bot...",
            default=existing.get("backstory") or "",
            required=True,
            max_length=4000,
        )
        self.traits_input = discord.ui.TextInput(
            label="Traits",
            style=discord.TextStyle.paragraph,
            placeholder="อธิบายนิสัยและบุคลิกของ Bot...",
            default=existing.get("traits") or "",
            required=True,
            max_length=4000,
        )

        self.add_item(self.name_input)
        self.add_item(self.backstory_input)
        self.add_item(self.traits_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)
        user_uuid = _discord_uuid(discord_id)

        name = self.name_input.value.strip()
        backstory = self.backstory_input.value.strip()
        traits_text = self.traits_input.value.strip()

        def _blocking_work():
            # 1. Upsert Supabase BotProfile
            bot_data = supa_db_manager.upsert_bot_profile(
                user_uuid,
                {"name": name, "backstory": backstory, "traits": traits_text},
            )
            bot_id = str(bot_data.get("bot_id", uuid.uuid4()))

            # 2. Save Bot node in Neo4j and link to User
            graph_db = graph_db_manager.load()
            graph_db.save_bot_profile(
                bot_id, discord_id, {"name": name, "backstory": backstory}
            )

            try:
                traits, conditions, emotions = update_bot_traits(bot_id, traits_text)
                try:
                    create_emotion_conditions(bot_id, conditions)
                except Exception as exc:
                    print(f"[bot_create] create_emotion_conditions failed: {exc}")
            except Exception as exc:
                traits, conditions, emotions = [], [], []

            # 4. Extract world views from backstory
            try:
                world_views = create_world_views_from_backstory(bot_id, backstory)
            except Exception as exc:
                print(f"[bot_create] create_world_views failed: {exc}")
                world_views = []

            try:
                index_backstory(bot_id, backstory)
            except Exception as exc:
                print(f"[bot_create] index_backstory failed: {exc}")

            return bot_id, traits, conditions, world_views

        bot_id, traits, conditions, world_views = await asyncio.to_thread(
            _blocking_work
        )

        # 6. Prepare response embed early so we can append warnings if needed
        embed = discord.Embed(title="✅ Bot สร้างเรียบร้อย!", color=discord.Color.green())

        # If extraction returned nothing, log and notify the user
        failures = []
        if not traits:
            failures.append("traits")
        if not world_views:
            failures.append("world_views")
        if not conditions:
            failures.append("emotion_conditions")

        if failures:
            # append a warning field to the embed and also write to console
            embed.add_field(
                name="⚠️ Extraction Warning",
                value=("No data for: " + ", ".join(failures)),
                inline=False,
            )
            print(
                f"[bot_create] Extraction returned empty: {failures}. See logs/extractor_failures.log for details."
            )

        embed.add_field(name="Name", value=name, inline=True)
        embed.add_field(
            name="Traits", value=f"{len(traits)} traits analyzed", inline=True
        )
        embed.add_field(
            name="World Views", value=f"{len(world_views)} extracted", inline=True
        )
        embed.add_field(
            name="Emotion Conditions", value=f"{len(conditions)} detected", inline=True
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        try:
            await interaction.followup.send(
                "❌ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง", ephemeral=True
            )
        except Exception:
            pass
        raise error


# ── Command group ───────────────────────────────────────────

bot_group = app_commands.Group(name="bot", description="จัดการ Bot ของคุณ")


@bot_group.command(name="create", description="สร้างหรืออัปเดต Bot ของคุณ")
async def bot_create(interaction: discord.Interaction) -> None:
    user_uuid = _discord_uuid(str(interaction.user.id))
    existing = await asyncio.to_thread(
        supa_db_manager.get_bot_profile_by_user, user_uuid
    )
    modal = BotCreateModal(existing)
    await interaction.response.send_modal(modal)


def register(tree: app_commands.CommandTree) -> None:
    tree.add_command(bot_group)
