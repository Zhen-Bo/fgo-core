"""
Gacha-related data models and enumerations.
"""

from enum import Enum


# Mapping from raw API integer type to GachaType string value
_GACHA_TYPE_MAP = {
    1: "stone",        # 聖晶石池
    2: "chargeStone",  # 付費石池 (legacy, not used in current game data)
    3: "friendPoint",  # 友情點數池
    7: "chargeStone",  # 付費確定池 (スタートダッシュ等)
}


class GachaType(str, Enum):
    """
    Gacha pool types.

    Inherits from str to allow direct string comparison and JSON serialization.
    """
    FRIEND_POINT = "friendPoint"  # 友情點數池 (type=3 in raw API)
    STONE = "stone"               # 聖晶石池 (type=1 in raw API)
    CHARGE_STONE = "chargeStone"  # 付費石池 (type=2 in raw API)
    PAY_GACHA = "payGacha"        # 付費抽卡
    UNKNOWN = "unknown"           # 未知類型

    @classmethod
    def from_int(cls, value: int) -> "GachaType":
        """
        Convert integer type from raw API to GachaType enum.

        Args:
            value: Integer value from mstGacha.type (1=stone, 2=chargeStone, 3=friendPoint)

        Returns:
            Corresponding GachaType enum value, or UNKNOWN if not recognized.
        """
        str_value = _GACHA_TYPE_MAP.get(value, "unknown")
        return cls.from_string(str_value)

    @classmethod
    def from_string(cls, value: str) -> "GachaType":
        """
        Convert string to GachaType enum.

        Args:
            value: String value from API (e.g., "friendPoint", "stone")

        Returns:
            Corresponding GachaType enum value, or UNKNOWN if not recognized.

        Example:
            >>> GachaType.from_string("friendPoint")
            <GachaType.FRIEND_POINT: 'friendPoint'>
            >>> GachaType.from_string("invalid")
            <GachaType.UNKNOWN: 'unknown'>
        """
        for member in cls:
            if member.value == value:
                return member
        return cls.UNKNOWN

    def is_free(self) -> bool:
        """Check if this gacha type uses free currency (FP)."""
        return self == GachaType.FRIEND_POINT

    def is_premium(self) -> bool:
        """Check if this gacha type requires paid currency."""
        return self in (GachaType.CHARGE_STONE, GachaType.PAY_GACHA)
