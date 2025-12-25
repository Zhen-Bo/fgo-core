"""Battle-related data models."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DropItem:
    """Item dropped from battle."""
    object_id: int
    original_num: int
    num: int

    @property
    def bonus_num(self) -> int:
        """Additional drops from bonuses."""
        return self.num - self.original_num


@dataclass
class FollowerInfo:
    """Support follower information."""
    user_id: int
    follower_type: int
    support_deck_id: str
    class_id: int
    equip_svt_id: int
    equip_limit_count: int
    svt_id: int = 0
    limit_count: int = 0


@dataclass
class FollowerListResult:
    """Result of follower list request."""
    success: bool
    followers: List[FollowerInfo] = field(default_factory=list)
    error_message: Optional[str] = None
    cooldown_remaining: float = 0.0  # Seconds remaining before refresh allowed


@dataclass
class RecoveryResult:
    """Result of AP recovery request."""
    success: bool
    current_ap: int = 0
    apple_type: int = 0
    error_message: Optional[str] = None


@dataclass
class BattleSetupResult:
    """Result of battle setup request."""
    success: bool
    battle_id: int = 0
    quest_id: int = 0
    quest_phase: int = 0
    enemy_deck_pages: int = 0
    enemy_unique_ids: List[int] = field(default_factory=list)
    my_deck_svt_count: int = 0
    drop_items: List[DropItem] = field(default_factory=list)
    current_ap: int = 0
    ap_cost: int = 0
    error_message: Optional[str] = None


@dataclass
class FriendshipUpdate:
    """Friendship/bond update after battle."""
    svt_id: int
    friendship_rank: int
    friendship: int


@dataclass
class BattleResultResponse:
    """Result of battle result submission."""
    success: bool
    friendship_updates: List[FriendshipUpdate] = field(default_factory=list)
    error_message: Optional[str] = None
