"""List past session entries in decoded, human-readable format.

Usage:
    python scripts/list_sessions.py              # last 10 entries (default)
    python scripts/list_sessions.py -n 5         # last 5 entries
    python scripts/list_sessions.py -t 176622453 # specific thread
    python scripts/list_sessions.py --all        # all threads
"""
import argparse
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")


def _load_usernames() -> dict[str, str]:
    """Map user_id -> username from patron_users.users."""
    client = MongoClient(MONGODB_URI)
    users = client["patron_users"]["users"].find({}, {"user_id": 1, "username": 1, "_id": 0})
    return {u["user_id"]: u.get("username", "") for u in users}


def _format_content(content) -> str:
    if isinstance(content, str):
        return content
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
                elif block.get("type") == "tool_use":
                    parts.append(f"[tool_call: {block.get('name', '?')}]")
                else:
                    parts.append(f"[{block.get('type', '?')}]")
            else:
                parts.append(str(block))
        return " ".join(parts)
    return str(content)


def _format_tool_content(content) -> str:
    text = _format_content(content)
    if len(text) > 200:
        return text[:200] + "..."
    return text


def print_session(saver, thread_id, usernames, verbose=False):
    config = {"configurable": {"thread_id": thread_id}}
    cp_tuple = saver.get_tuple(config)
    if not cp_tuple:
        print(f"  (no checkpoint found)")
        return

    cp = cp_tuple.checkpoint
    messages = cp.get("channel_values", {}).get("messages", [])
    metadata = cp_tuple.metadata or {}

    username = usernames.get(thread_id, "")
    print(f"  Thread ID : {thread_id}")
    if username:
        print(f"  Username  : @{username}")
    print(f"  Messages  : {len(messages)}")
    print(f"  Step      : {metadata.get('step', '?')}")
    print()

    for msg in messages:
        role = getattr(msg, "type", "?")
        content = getattr(msg, "content", "")

        if role == "tool":
            tool_name = getattr(msg, "name", "")
            formatted = _format_tool_content(content)
            print(f"    [{role}:{tool_name}] {formatted}")
        elif role == "ai":
            tool_calls = getattr(msg, "tool_calls", None)
            text = _format_content(content)
            if tool_calls:
                calls = ", ".join(tc.get("name", "?") for tc in tool_calls)
                if text:
                    print(f"    [{role}] {text}")
                print(f"    [{role}:tool_calls] {calls}")
            else:
                print(f"    [{role}] {text}")
        else:
            text = _format_content(content)
            if not verbose and len(text) > 300:
                text = text[:300] + "..."
            label = f"@{username}" if username else role
            print(f"    [{label}] {text}")

    print()


def main():
    parser = argparse.ArgumentParser(description="List past session entries.")
    parser.add_argument("-n", type=int, default=10, help="Number of entries to show (default: 10)")
    parser.add_argument("-t", "--thread", type=str, help="Show specific thread ID")
    parser.add_argument("--all", action="store_true", help="Show all threads")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show full message content")
    args = parser.parse_args()

    if not MONGODB_URI:
        print("Error: MONGODB_URI not set", file=sys.stderr)
        sys.exit(1)

    usernames = _load_usernames()

    with MongoDBSaver.from_conn_string(MONGODB_URI, "patron_sessions") as saver:
        if args.thread:
            print(f"=== Session: {args.thread} ===")
            print_session(saver, args.thread, usernames, verbose=args.verbose)
            return

        threads = saver.db["checkpoints"].distinct("thread_id")

        if not threads:
            print("No sessions found.")
            return

        # Sort by latest checkpoint_id (descending) per thread
        pipeline = [
            {"$sort": {"checkpoint_id": -1}},
            {"$group": {"_id": "$thread_id", "latest": {"$first": "$checkpoint_id"}}},
            {"$sort": {"latest": -1}},
        ]
        if not args.all:
            pipeline.append({"$limit": args.n})

        sorted_threads = [
            doc["_id"] for doc in saver.db["checkpoints"].aggregate(pipeline)
        ]

        print(f"Found {len(threads)} total sessions, showing {len(sorted_threads)}:\n")

        for tid in sorted_threads:
            print(f"{'=' * 60}")
            print_session(saver, tid, usernames, verbose=args.verbose)


if __name__ == "__main__":
    main()
