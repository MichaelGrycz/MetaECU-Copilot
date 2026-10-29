"""
Catalog ingestion + physical map extraction for EDC16C39.

The master catalog (BOSCH_EDC16C39_1037389375_COMPLETE_CATALOG.json) contains
774 entries. Field semantics verified against the stock binary and the legacy
audit scripts:

* ``cols`` = number of X breakpoints, ``rows`` = number of Y breakpoints
* X axis: ``cols`` values at ``x_addr``; Y axis: ``rows`` values at ``y_addr``
  (``y_addr == 0`` for CURVE / VALUE entries)
* Z area: row-major, ``rows * cols`` cells starting at ``z_start``,
  each ``elem_bytes`` wide, big-endian, physical = raw * factor + offset.
  Confirmed e.g. for EngM_trqFrc_MAP (16x16) and Rail_pSetPointBase_MAP:
  catalog axis addresses are the *data* starts (the 4-byte header-count form
  used by some legacy scripts sits 4 bytes earlier and is not used here).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from .flash_loader import FlashImage


@dataclass(frozen=True)
class MapEntry:
    symbol: str
    title: str
    module: str
    type: str  # MAP | CURVE | VALUE
    rows: int
    cols: int
    elem_bytes: int
    signed: bool
    z_start: int
    z_end: int
    z_factor: float
    z_offset: float
    z_unit: str
    x_addr: int
    x_factor: float
    x_offset: float
    x_signed: bool
    x_unit: str
    y_addr: int
    y_factor: float
    y_offset: float
    y_signed: bool
    y_unit: str
    source: str

    @property
    def cells(self) -> int:
        return self.rows * self.cols

    @classmethod
    def from_dict(cls, d: dict) -> "MapEntry":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__})


@dataclass
class MapData:
    """Physical (scaled) view of one catalog entry."""

    entry: MapEntry
    x: np.ndarray  # shape (cols,)
    y: np.ndarray  # shape (rows,) — empty for CURVE/VALUE
    z: np.ndarray  # shape (rows, cols), physical units

    @property
    def symbol(self) -> str:
        return self.entry.symbol

    def z_max(self) -> float:
        return float(np.max(self.z)) if self.z.size else 0.0

    def z_min(self) -> float:
        return float(np.min(self.z)) if self.z.size else 0.0

    def summary(self) -> dict:
        return {
            "symbol": self.symbol,
            "title": self.entry.title,
            "type": self.entry.type,
            "rows": self.entry.rows,
            "cols": self.entry.cols,
            "x_unit": self.entry.x_unit,
            "y_unit": self.entry.y_unit,
            "z_unit": self.entry.z_unit,
            "z_min": round(self.z_min(), 4),
            "z_max": round(self.z_max(), 4),
            "x_first": float(self.x[0]) if self.x.size else None,
            "x_last": float(self.x[-1]) if self.x.size else None,
            "y_first": float(self.y[0]) if self.y.size else None,
            "y_last": float(self.y[-1]) if self.y.size else None,
        }


class Catalog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"Catalog must be a JSON list, got {type(raw)}")
        self.entries: list[MapEntry] = [MapEntry.from_dict(d) for d in raw]
        self._by_symbol = {e.symbol: e for e in self.entries}

    def __len__(self) -> int:
        return len(self.entries)

    def get(self, symbol: str) -> MapEntry:
        try:
            return self._by_symbol[symbol]
        except KeyError:
            raise KeyError(
                f"Symbol not in catalog: {symbol!r}. "
                f"Try search({symbol!r}) — names are exact Bosch symbols."
            ) from None

    def search(self, needle: str) -> list[MapEntry]:
        n = needle.lower()
        return [
            e
            for e in self.entries
            if n in e.symbol.lower() or n in e.title.lower() or n in e.module.lower()
        ]

    def symbols(self) -> list[str]:
        return sorted(self._by_symbol)

    # ------------------------------------------------------------- reading
    def _axis(
        self,
        flash: FlashImage,
        addr: int,
        count: int,
        factor: float,
        offset: float,
        signed: bool,
    ) -> np.ndarray:
        if addr == 0 or count == 0:
            return np.empty(0, dtype=np.float64)
        raw = flash.read_array(addr, count, elem_bytes=2, signed=signed)
        return raw.astype(np.float64) * factor + offset

    def read_map(self, flash: FlashImage, symbol: str) -> MapData:
        e = self.get(symbol)
        x = self._axis(flash, e.x_addr, e.cols, e.x_factor, e.x_offset, e.x_signed)
        y = self._axis(flash, e.y_addr, e.rows, e.y_factor, e.y_offset, e.y_signed)
        raw = flash.read_array(e.z_start, e.cells, e.elem_bytes, e.signed)
        z = raw.astype(np.float64) * e.z_factor + e.z_offset
        return MapData(entry=e, x=x, y=y, z=z.reshape(e.rows, e.cols))

    # ------------------------------------------------------------- writing
    def write_map(self, flash: FlashImage, data: MapData) -> None:
        """Write physical Z values back, quantising to the raw grid."""
        e = data.entry
        if data.z.shape != (e.rows, e.cols):
            raise ValueError(
                f"Shape mismatch for {e.symbol}: {data.z.shape} vs {(e.rows, e.cols)}"
            )
        raw = np.round((data.z - e.z_offset) / e.z_factor)
        if e.signed:
            lo, hi = (-(2 ** (8 * e.elem_bytes - 1)), 2 ** (8 * e.elem_bytes - 1) - 1)
        else:
            lo, hi = (0, 2 ** (8 * e.elem_bytes) - 1)
        raw = np.clip(raw, lo, hi)
        flash.write_array_raw(e.z_start, raw.astype(np.int64), e.elem_bytes, e.signed)

    def write_curve_value(
        self, flash: FlashImage, symbol: str, index: int, physical: float
    ) -> None:
        e = self.get(symbol)
        raw = int(round((physical - e.z_offset) / e.z_factor))
        flash.write_raw(e.z_start + index * e.elem_bytes, raw, e.elem_bytes, e.signed)
