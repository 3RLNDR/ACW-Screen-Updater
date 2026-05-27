from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    public_dir: Path
    video_dir: Path
    image_dir: Path
    qr_dir: Path
    data_dir: Path
    database_path: Path

    @classmethod
    def from_root(cls, root_dir: Path) -> "AppConfig":
        public_dir = root_dir / "public"
        data_dir = root_dir / "data"
        return cls(
            root_dir=root_dir,
            public_dir=public_dir,
            video_dir=public_dir / "cache" / "videos",
            image_dir=public_dir / "cache" / "images",
            qr_dir=public_dir / "cache" / "qr",
            data_dir=data_dir,
            database_path=data_dir / "acw-display.sqlite3",
        )
