from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class DisplayDatabase:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                create table if not exists videos (
                    id text primary key,
                    title text not null,
                    filename text not null,
                    storage_path text not null,
                    poster_path text,
                    mime_type text not null,
                    duration_seconds integer,
                    enabled integer not null default 1,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp
                );

                create table if not exists event_video_associations (
                    event_id text primary key,
                    video_id text not null references videos(id),
                    enabled integer not null default 1,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp
                );
                """
            )

    def save_video(
        self,
        *,
        video_id: str,
        title: str,
        filename: str,
        storage_path: str,
        mime_type: str,
        duration_seconds: int | None,
        poster_path: str | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                insert into videos (
                    id, title, filename, storage_path, poster_path, mime_type, duration_seconds, enabled
                ) values (
                    :video_id, :title, :filename, :storage_path, :poster_path, :mime_type, :duration_seconds, 1
                )
                on conflict(id) do update set
                    title=excluded.title,
                    filename=excluded.filename,
                    storage_path=excluded.storage_path,
                    poster_path=excluded.poster_path,
                    mime_type=excluded.mime_type,
                    duration_seconds=excluded.duration_seconds,
                    updated_at=current_timestamp
                """,
                {
                    "video_id": video_id,
                    "title": title,
                    "filename": filename,
                    "storage_path": storage_path,
                    "poster_path": poster_path,
                    "mime_type": mime_type,
                    "duration_seconds": duration_seconds,
                },
            )

    def list_videos(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("select * from videos order by created_at desc, id asc").fetchall()
        return [dict(row) for row in rows]

    def get_video_map(self) -> dict[str, dict[str, Any]]:
        return {row["id"]: row for row in self.list_videos()}

    def set_event_video(self, *, event_id: str, video_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                insert into event_video_associations (event_id, video_id, enabled)
                values (?, ?, 1)
                on conflict(event_id) do update set
                    video_id=excluded.video_id,
                    enabled=1,
                    updated_at=current_timestamp
                """,
                (event_id, video_id),
            )

    def clear_event_video(self, event_id: str) -> None:
        with self.connect() as connection:
            connection.execute("delete from event_video_associations where event_id = ?", (event_id,))

    def list_event_video_map(self) -> dict[str, str]:
        with self.connect() as connection:
            rows = connection.execute(
                "select event_id, video_id from event_video_associations where enabled = 1"
            ).fetchall()
        return {row["event_id"]: row["video_id"] for row in rows}
