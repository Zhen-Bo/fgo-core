"""Follower service for support friend list."""

import time

from fgo_sdk.client.fgo_client import FgoClient
from fgo_sdk.models.battle_data import FollowerInfo, FollowerListResult

# Refresh cooldown in seconds
REFRESH_COOLDOWN = 11.0


class FollowerService:
    """Service for follower/support friend operations."""

    def __init__(self, client: FgoClient):
        self.client = client
        self._last_refresh_time: float = 0.0

    def get_follower_list(
        self,
        quest_id: int,
        quest_phase: int,
        refresh: bool = True,
        is_event: bool = False,
    ) -> FollowerListResult:
        """
        Get available support followers for a quest.

        Args:
            quest_id: Quest ID to get followers for
            quest_phase: Quest phase number
            refresh: Whether to refresh the follower list
            is_event: Whether this is an event quest (uses different support table)

        Returns:
            FollowerListResult with list of available followers
        """
        try:
            # Check refresh cooldown
            if refresh:
                elapsed = time.time() - self._last_refresh_time
                if elapsed < REFRESH_COOLDOWN:
                    remaining = REFRESH_COOLDOWN - elapsed
                    return FollowerListResult(
                        success=False,
                        error_message=f"Refresh cooldown: {remaining:.1f}s remaining",
                        cooldown_remaining=remaining,
                    )
                self._last_refresh_time = time.time()

            data = self.client.create_form_data({
                "questId": str(quest_id),
                "questPhase": str(quest_phase),
                "refresh": "1" if refresh else "0",
            })

            response = self.client.post("/follower/list", data, "Follower List")

            # Parse response
            cache = response.get("cache", {})
            updated = cache.get("updated", {})
            user_follower = updated.get("userFollower", [{}])[0]
            follower_info_list = user_follower.get("followerInfo", [])

            followers = []
            table_name = "eventUserSvtLeaderHash" if is_event else "userSvtLeaderHash"

            for follower_data in follower_info_list:
                user_id = follower_data.get("userId", 0)
                follower_type = follower_data.get("type", 0)
                support_array = follower_data.get(table_name, [])

                for support in support_array:
                    class_id = support.get("classId", 0)
                    support_deck_id = str(support.get("supportDeckId", 1))
                    svt_id = support.get("svtId", 0)
                    limit_count = support.get("limitCount", 0)

                    # Get equip info
                    equip_target = support.get("equipTarget1", {})
                    equip_svt_id = equip_target.get("svtId", 0)
                    equip_limit_count = equip_target.get("limitCount", 0)

                    followers.append(FollowerInfo(
                        user_id=user_id,
                        follower_type=follower_type,
                        support_deck_id=support_deck_id,
                        class_id=class_id,
                        equip_svt_id=equip_svt_id,
                        equip_limit_count=equip_limit_count,
                        svt_id=svt_id,
                        limit_count=limit_count,
                    ))

            return FollowerListResult(
                success=True,
                followers=followers,
            )

        except Exception as e:
            return FollowerListResult(
                success=False,
                error_message=str(e),
            )
