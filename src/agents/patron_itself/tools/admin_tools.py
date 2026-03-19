import os

from langchain_core.tools import tool
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from agents.patron_itself.repositories.memories_repository import MemoriesRepository

MONGODB_URI = os.getenv("MONGODB_URI")

ADMIN_USER_ID = "176622453"


def create_admin_tools(memories_repo: MemoriesRepository) -> list:
    """Create admin-only tools for inspecting sessions and memories of any user."""

    @tool
    def admin_list_users() -> list[dict]:
        """List all users in the system with their basic info (user_id, username, timezone, subscription status)."""
        client = MongoClient(MONGODB_URI)
        users = client["patron_users"]["users"].find(
            {}, {"_id": 0, "user_id": 1, "username": 1, "timezone": 1, "subscription_expires_at": 1}
        )
        return [
            {
                "user_id": u.get("user_id"),
                "username": u.get("username"),
                "timezone": u.get("timezone"),
                "subscription_expires_at": str(u["subscription_expires_at"]) if u.get("subscription_expires_at") else None,
            }
            for u in users
        ]

    @tool
    def admin_read_user_memories(
        target_user_id: str,
    ) -> list[dict]:
        """Read all memories for a given user. Returns list of memories with id, text, metadata, and created_at."""
        return memories_repo.find_by_date_range(target_user_id)

    @tool
    def admin_search_user_memories(
        target_user_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        """Search memories of any user by semantic similarity."""
        return memories_repo.search(target_user_id, query, limit=limit)

    @tool
    def admin_list_sessions(
        target_user_id: str | None = None,
        count: int = 10,
    ) -> list[dict]:
        """List conversation sessions. Optionally filter by user_id. Returns thread_id, message count, and last step."""
        with MongoDBSaver.from_conn_string(MONGODB_URI, "patron_sessions") as saver:
            pipeline = [
                {"$sort": {"checkpoint_id": -1}},
                {"$group": {"_id": "$thread_id", "latest": {"$first": "$checkpoint_id"}}},
                {"$sort": {"latest": -1}},
            ]
            if target_user_id:
                pipeline.insert(0, {"$match": {"thread_id": target_user_id}})
            pipeline.append({"$limit": count})

            threads = [doc["_id"] for doc in saver.db["checkpoints"].aggregate(pipeline)]

            results = []
            for tid in threads:
                config = {"configurable": {"thread_id": tid}}
                cp_tuple = saver.get_tuple(config)
                if not cp_tuple:
                    continue
                cp = cp_tuple.checkpoint
                messages = cp.get("channel_values", {}).get("messages", [])
                metadata = cp_tuple.metadata or {}
                results.append({
                    "thread_id": tid,
                    "message_count": len(messages),
                    "step": metadata.get("step", "?"),
                })
            return results

    @tool
    def admin_read_session(
        thread_id: str,
        last_n_messages: int = 50,
    ) -> list[dict]:
        """Read the conversation history of a specific session/thread. Returns the last N messages."""
        with MongoDBSaver.from_conn_string(MONGODB_URI, "patron_sessions") as saver:
            config = {"configurable": {"thread_id": thread_id}}
            cp_tuple = saver.get_tuple(config)
            if not cp_tuple:
                return [{"error": f"No session found for thread_id: {thread_id}"}]

            cp = cp_tuple.checkpoint
            messages = cp.get("channel_values", {}).get("messages", [])
            messages = messages[-last_n_messages:]

            result = []
            for msg in messages:
                role = getattr(msg, "type", "?")
                content = getattr(msg, "content", "")

                entry = {"role": role}

                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                parts.append(block["text"])
                            elif block.get("type") == "media":
                                parts.append(f"[audio: {block.get('mime_type', '?')}]")
                            elif block.get("type") == "image_url":
                                parts.append("[image]")
                            else:
                                parts.append(f"[{block.get('type', '?')}]")
                        else:
                            parts.append(str(block))
                    entry["content"] = " ".join(parts)
                else:
                    entry["content"] = str(content) if content else ""

                if role == "tool":
                    entry["tool_name"] = getattr(msg, "name", "")
                    # Truncate long tool outputs
                    if len(entry["content"]) > 500:
                        entry["content"] = entry["content"][:500] + "..."
                elif role == "ai":
                    tool_calls = getattr(msg, "tool_calls", None)
                    if tool_calls:
                        entry["tool_calls"] = [tc.get("name", "?") for tc in tool_calls]

                result.append(entry)
            return result

    return [admin_list_users, admin_read_user_memories, admin_search_user_memories,
            admin_list_sessions, admin_read_session]
