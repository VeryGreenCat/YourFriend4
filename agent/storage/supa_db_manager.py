from __future__ import annotations

from typing import Optional

from supabase import Client, create_client

from agent.utils import get_config

_client: Optional[Client] = None


def load() -> Client:
    """Return the singleton Supabase client (uses service role key)."""
    global _client
    if _client is None:
        config = get_config()
        _client = create_client(config.Supabase_URL, config.Supabase_Service_Key)
    return _client


def get_or_create_profile(user_id: str, email: str, user_metadata: dict) -> dict:
    client = load()

    # Try to fetch an existing profile
    result = (
        client.table("UserProfile")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]

    # Build profile from JWT metadata — display_name and username are NOT NULL
    username = (
        user_metadata.get("username")
        or user_metadata.get("preferred_username")
        or (email.split("@")[0] if email else user_id)
    )
    display_name = (
        user_metadata.get("full_name")
        or user_metadata.get("name")
        or username
    )

    profile_data = {
        "user_id": user_id,
        "email": email or None,
        "username": username,
        "display_name": display_name,
        "avatar_url": user_metadata.get("avatar_url") or None,
        "gender": user_metadata.get("gender") or None,
        "age": user_metadata.get("age") or None,
    }

    insert_result = (
        client.table("UserProfile").insert(profile_data).execute()
    )
    return insert_result.data[0] if insert_result.data else profile_data
