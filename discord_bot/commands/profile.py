from __future__ import annotations

import os
import sys
import uuid

import discord
from discord import app_commands

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)

from agent.storage import graph_db_manager, supa_db_manager

_DISCORD_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _discord_uuid(discord_id: str) -> str:
    """Return a deterministic UUID string derived from a Discord snowflake ID."""
    return str(uuid.uuid5(_DISCORD_NS, f"discord:{discord_id}"))


class ProfileModal(discord.ui.Modal, title="ตั้งค่าโปรไฟล์"):
    def __init__(self, existing: dict | None = None) -> None:
        super().__init__()
        existing = existing or {}

        self.display_name_input = discord.ui.TextInput(
            label="Display Name",
            placeholder="ชื่อที่แสดง",
            default=existing.get("display_name") or "",
            required=True,
            max_length=80,
        )
        self.username_input = discord.ui.TextInput(
            label="Username",
            placeholder="ชื่อผู้ใช้",
            default=existing.get("username") or "",
            required=True,
            max_length=50,
        )
        self.age_input = discord.ui.TextInput(
            label="Age",
            placeholder="อายุ (ตัวเลขเท่านั้น)",
            default=str(existing["age"]) if existing.get("age") is not None else "",
            required=False,
            max_length=3,
        )
        self.gender_input = discord.ui.TextInput(
            label="Gender",
            placeholder="เช่น male, female, other",
            default=existing.get("gender") or "",
            required=False,
            max_length=30,
        )

        self.add_item(self.display_name_input)
        self.add_item(self.username_input)
        self.add_item(self.age_input)
        self.add_item(self.gender_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        age: int | None = None
        age_raw = self.age_input.value.strip()
        if age_raw:
            if not age_raw.isdigit():
                await interaction.followup.send("❌ อายุต้องเป็นตัวเลขเท่านั้น", ephemeral=True)
                return
            age = int(age_raw)

        discord_id = str(interaction.user.id)
        user_uuid = _discord_uuid(discord_id)
        profile_data = {
            "display_name": self.display_name_input.value.strip(),
            "username": self.username_input.value.strip(),
            "age": age,
            "gender": self.gender_input.value.strip() or None,
        }

        # Upsert Supabase UserProfile (UUID key)
        supa_db_manager.upsert_profile(user_uuid, profile_data)

        # Create or update Neo4j User node (raw Discord snowflake as ID)
        graph_db = graph_db_manager.load()
        graph_db.save_user(discord_id, {
            "name": profile_data["display_name"],
            "age": profile_data["age"],
            "gender": profile_data["gender"],
        })

        embed = discord.Embed(title="✅ โปรไฟล์อัปเดตแล้ว", color=discord.Color.green())
        embed.add_field(name="Display Name", value=profile_data["display_name"], inline=True)
        embed.add_field(name="Username", value=profile_data["username"], inline=True)
        if profile_data["age"] is not None:
            embed.add_field(name="Age", value=str(profile_data["age"]), inline=True)
        if profile_data["gender"]:
            embed.add_field(name="Gender", value=profile_data["gender"], inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.followup.send("❌ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง", ephemeral=True)
        raise error


def register(tree: app_commands.CommandTree) -> None:
    @tree.command(name="profile", description="ดูหรือแก้ไขโปรไฟล์ของคุณ")
    async def profile(interaction: discord.Interaction) -> None:
        user_uuid = _discord_uuid(str(interaction.user.id))
        existing = supa_db_manager.get_profile(user_uuid)
        modal = ProfileModal(existing)
        await interaction.response.send_modal(modal)
