from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "agent"))

from agent.storage import graph_db_manager
from api.config import get_api_config
from api.middleware import JWTMiddleware

app = FastAPI(
    title="YourFriend API",
    description="API for managing users and their data in the YourFriend graph database.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(JWTMiddleware)


class UserInfo(BaseModel):
    name: Optional[str] = Field(default=None, examples=["Alice"])
    age: Optional[int] = Field(default=None, examples=[25])
    gender: Optional[str] = Field(default=None, examples=["female"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"name": "Alice", "age": 25, "gender": "female"}
            ]
        }
    }


class SaveUserResponse(BaseModel):
    message: str
    user: dict[str, Any]


@app.post(
    "/users/{user_id}",
    response_model=SaveUserResponse,
    summary="Create or update a user",
    description="Creates a new user node or updates an existing one in Neo4j using MERGE.",
    tags=["Users"],
    responses={
        200: {"description": "User created or updated successfully"},
        500: {"description": "Database error"},
    },
)
def save_user(user_id: str, user_info: UserInfo):
    db = graph_db_manager.load()
    result = db.save_user(user_id, user_info.model_dump(exclude_none=False))
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to save user")
    return {"message": f"User {user_id} saved successfully", "user": dict(result["u"])}
