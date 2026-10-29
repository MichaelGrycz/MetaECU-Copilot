"""Binary Core Engine: flash I/O and map extraction for Bosch EDC16C39."""

from .flash_loader import (
    CHECKSUM_ADDR,
    CHECKSUM_REGION,
    EXPECTED_SIZE,
    TARGET_CHECKSUM,
    FlashImage,
    load_flash,
)
from .map_reader import Catalog, MapData

__all__ = [
    "EXPECTED_SIZE",
    "CHECKSUM_ADDR",
    "CHECKSUM_REGION",
    "TARGET_CHECKSUM",
    "FlashImage",
    "load_flash",
    "Catalog",
    "MapData",
]
