from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RatioSpec:
    name: str
    width: int
    height: int
    image_width: int
    image_height: int
    panel_x: int
    panel_width: int
    category_x: int
    category_y: int
    title_x: int
    title_y: int
    title_width: int
    meta_x: int
    meta_y: int
    note_x: int
    note_y: int
    qr_x: int
    qr_y: int
    qr_size: int


RATIO_SPECS = {
    "16x9": RatioSpec(
        name="16x9",
        width=1600,
        height=900,
        image_width=899,
        image_height=788,
        panel_x=945,
        panel_width=599,
        category_x=987,
        category_y=128,
        title_x=983,
        title_y=184,
        title_width=561,
        meta_x=987,
        meta_y=482,
        note_x=987,
        note_y=504,
        qr_x=1141,
        qr_y=646,
        qr_size=164,
    ),
    "4x3": RatioSpec(
        name="4x3",
        width=1200,
        height=900,
        image_width=668,
        image_height=788,
        panel_x=714,
        panel_width=430,
        category_x=756,
        category_y=128,
        title_x=752,
        title_y=184,
        title_width=392,
        meta_x=756,
        meta_y=482,
        note_x=756,
        note_y=504,
        qr_x=886,
        qr_y=640,
        qr_size=156,
    ),
}


def get_ratio_spec(name: str) -> RatioSpec:
    if name not in RATIO_SPECS:
        raise ValueError(f"Unsupported ratio: {name}")
    return RATIO_SPECS[name]
