"""
Zero-guesswork flash loader for Bosch EDC16C39 (Saab 9-3 1.9 TiD, SW 1037389375).

The flash image is exactly 2 MiB (2 097 152 bytes). All integers stored in the
calibration area are big-endian (Motorola MPC562). The file-level checksum used
by this project and verified by the existing audit scripts
(``audit_transmission_f40_dmf.py``, ``audit_v12_comprehensive.py``) is:

    sum of every 32-bit big-endian word in [0x1C0000, 0x1FE000)
        == 0xD01FE500   (mod 2**32)

The correction word lives at 0x1FDFFC (the last word of that range), so
``fix_checksum`` rewrites it to ``TARGET - (sum of all other words)`` and the
invariant above holds for any calibration bytes inside the range.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

EXPECTED_SIZE = 2_097_152
CHECKSUM_REGION = (0x1C0000, 0x1FE000)
CHECKSUM_ADDR = 0x1FDFFC
TARGET_CHECKSUM = 0xD01FE500

_DTYPES = {
    ("H", 2, False): np.dtype(">u2"),
    ("h", 2, True): np.dtype(">i2"),
    ("B", 1, False): np.dtype("u1"),
    ("b", 1, True): np.dtype("i1"),
    ("I", 4, False): np.dtype(">u4"),
    ("i", 4, True): np.dtype(">i4"),
}
_FMT = {
    (2, False): "H",
    (2, True): "h",
    (1, False): "B",
    (1, True): "b",
    (4, False): "I",
    (4, True): "i",
}


class FlashImage:
    """Mutable, validated 2 MiB EDC16C39 flash image."""

    def __init__(self, data: bytes | bytearray, source: str = "<memory>"):
        raw = bytearray(data)
        if len(raw) != EXPECTED_SIZE:
            raise ValueError(
                f"Invalid flash size: {len(raw)} bytes, expected {EXPECTED_SIZE} "
                f"(2 MiB EDC16C39). Source: {source}"
            )
        self._buf = raw
        self.source = source

    # ------------------------------------------------------------------ I/O
    @property
    def buffer(self) -> bytearray:
        return self._buf

    def to_bytes(self) -> bytes:
        return bytes(self._buf)

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(self._buf)
        return p

    def clone(self) -> "FlashImage":
        return FlashImage(bytes(self._buf), source=self.source + " (clone)")

    # ---------------------------------------------------------------- reads
    def _check(self, addr: int, size: int) -> None:
        if addr < 0 or addr + size > EXPECTED_SIZE:
            raise IndexError(
                f"Read out of range: 0x{addr:06X}+{size} beyond {EXPECTED_SIZE}"
            )

    def read_block(self, addr: int, size: int) -> bytes:
        self._check(addr, size)
        return bytes(self._buf[addr : addr + size])

    def read_u8(self, addr: int) -> int:
        self._check(addr, 1)
        return self._buf[addr]

    def read_s8(self, addr: int) -> int:
        return struct.unpack_from("b", self._buf, addr)[0]

    def read_u16be(self, addr: int) -> int:
        return struct.unpack_from(">H", self._buf, addr)[0]

    def read_s16be(self, addr: int) -> int:
        return struct.unpack_from(">h", self._buf, addr)[0]

    def read_u16le(self, addr: int) -> int:
        return struct.unpack_from("<H", self._buf, addr)[0]

    def read_s16le(self, addr: int) -> int:
        return struct.unpack_from("<h", self._buf, addr)[0]

    def read_u32be(self, addr: int) -> int:
        return struct.unpack_from(">I", self._buf, addr)[0]

    def read_array(
        self, addr: int, count: int, elem_bytes: int = 2, signed: bool = False
    ) -> np.ndarray:
        """Return raw (unscaled) big-endian values as an int64 numpy array."""
        self._check(addr, count * elem_bytes)
        dt = {
            (2, False): ">u2",
            (2, True): ">i2",
            (1, False): "u1",
            (1, True): "i1",
            (4, False): ">u4",
            (4, True): ">i4",
        }[(elem_bytes, signed)]
        arr = np.frombuffer(
            bytes(self._buf[addr : addr + count * elem_bytes]), dtype=np.dtype(dt)
        )
        return arr.astype(np.int64)

    # --------------------------------------------------------------- writes
    def write_block(self, addr: int, payload: bytes) -> None:
        self._check(addr, len(payload))
        self._buf[addr : addr + len(payload)] = payload

    def write_u32be(self, addr: int, value: int) -> None:
        struct.pack_into(">I", self._buf, addr, value & 0xFFFFFFFF)

    def write_raw(
        self, addr: int, raw_value: int, elem_bytes: int = 2, signed: bool = False
    ) -> None:
        fmt = ">" + _FMT[(elem_bytes, signed)]
        struct.pack_into(fmt, self._buf, addr, int(raw_value))

    def write_array_raw(
        self, addr: int, values: np.ndarray, elem_bytes: int = 2, signed: bool = False
    ) -> None:
        flat = np.asarray(values).ravel()
        dt = {
            (2, False): ">u2",
            (2, True): ">i2",
            (1, False): "u1",
            (1, True): "i1",
            (4, False): ">u4",
            (4, True): ">i4",
        }[(elem_bytes, signed)]
        payload = flat.astype(np.dtype(dt)).tobytes()
        self.write_block(addr, payload)

    # ------------------------------------------------------------- checksum
    def compute_checksum(self) -> int:
        lo, hi = CHECKSUM_REGION
        words = np.frombuffer(bytes(self._buf[lo:hi]), dtype=np.dtype(">u4"))
        return int(words.sum(dtype=np.uint64)) & 0xFFFFFFFF

    def checksum_ok(self) -> bool:
        return self.compute_checksum() == TARGET_CHECKSUM

    def fix_checksum(self) -> int:
        """Rewrite the correction word at 0x1FDFFC so the region sum matches."""
        lo, hi = CHECKSUM_REGION
        words = np.frombuffer(bytes(self._buf[lo:hi]), dtype=np.dtype(">u4")).astype(
            np.int64
        )
        idx = (CHECKSUM_ADDR - lo) // 4
        others = int((words.sum() - words[idx]) & 0xFFFFFFFF)
        correction = (TARGET_CHECKSUM - others) & 0xFFFFFFFF
        self.write_u32be(CHECKSUM_ADDR, correction)
        assert self.checksum_ok(), "checksum fix failed"
        return correction

    # ----------------------------------------------------------------- misc
    def diff_count(self, other: "FlashImage") -> int:
        return int(
            np.count_nonzero(
                np.frombuffer(bytes(self._buf), dtype=np.uint8)
                != np.frombuffer(bytes(other._buf), dtype=np.uint8)
            )
        )

    @property
    def raw(self) -> bytearray:
        return self._buf

    def __len__(self) -> int:
        return EXPECTED_SIZE

    def __repr__(self) -> str:
        return (
            f"FlashImage({self.source!r}, size={EXPECTED_SIZE}, "
            f"checksum=0x{self.compute_checksum():08X}, ok={self.checksum_ok()})"
        )


def load_flash(path: str | Path) -> FlashImage:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Flash file not found: {p}")
    return FlashImage(p.read_bytes(), source=str(p))
