"""Battle service for quest battles."""

import gzip
import random

import msgpack

from fgo_sdk.client.fgo_client import FgoClient
from fgo_sdk.models.battle_data import (
    BattleResultResponse,
    BattleSetupResult,
    DropItem,
    FriendshipUpdate,
)
from fgo_sdk.utils.battle_crypto import calc_battle_status, cat_game5


# Command card types for fake battle logs
BATTLE_LOGS_LIST = [
    "1B", "1C", "1D",  # Servant 1: Arts, Buster, Quick
    "2B", "2C", "2D",  # Servant 2: Arts, Buster, Quick
    "3B", "3C", "3D",  # Servant 3: Arts, Buster, Quick
]


class BattleService:
    """Service for battle operations."""

    def __init__(self, client: FgoClient):
        self.client = client

    def battle_scenario(self, quest_id: int, quest_phase: int) -> bool:
        """
        Get battle scenario data (required before setup).

        Args:
            quest_id: Quest ID
            quest_phase: Quest phase number

        Returns:
            True if successful
        """
        try:
            data = self.client.create_form_data({
                "questId": str(quest_id),
                "questPhase": str(quest_phase),
                "routeSelect": "[]",
            })

            self.client.post("/battle/scenario", data, "Battle Scenario")
            return True

        except Exception:
            return False

    def battle_setup(
        self,
        quest_id: int,
        quest_phase: int,
        deck_id: int,
        follower_id: int,
        follower_type: int,
        follower_class_id: int,
        support_deck_id: str = "1",
    ) -> BattleSetupResult:
        """
        Start a battle and get enemy/drop info.

        Args:
            quest_id: Quest ID
            quest_phase: Quest phase number
            deck_id: Player's active deck ID
            follower_id: Support follower's user ID
            follower_type: Follower type (0=stranger, 1=non-friend, 2=friend)
            follower_class_id: Follower's class ID
            support_deck_id: Follower's support deck ID

        Returns:
            BattleSetupResult with battle info and drops
        """
        try:
            data = self.client.create_form_data({
                "activeDeckId": str(deck_id),
                "boostId": "0",
                "campaignItemId": "0",
                "choiceRandomLimitCounts": "{}",
                "enemySelect": "0",
                "followerClassId": str(follower_class_id),
                "followerId": str(follower_id),
                "followerRandomLimitCount": "0",
                "followerSupportDeckId": support_deck_id,
                "followerType": str(follower_type),
                "itemId": "0",
                "questId": str(quest_id),
                "questPhase": str(quest_phase),
                "questSelect": "0",
                "routeSelect": "[]",
                "userEquipId": "0",
            })

            response = self.client.post("/battle/setup", data, "Battle Setup")

            # Parse response
            cache = response.get("cache", {})
            replaced = cache.get("replaced", {})
            battle_data = replaced.get("battle", [{}])[0]

            battle_id = battle_data.get("id", 0)
            battle_info = battle_data.get("battleInfo", {})

            # My deck info
            my_deck = battle_info.get("myDeck", {})
            my_deck_svts = my_deck.get("svts", [])
            my_deck_svt_count = len(my_deck_svts)

            # Enemy deck info
            enemy_deck = battle_info.get("enemyDeck", [])
            enemy_deck_pages = len(enemy_deck)

            # Get enemy unique IDs from last page
            enemy_unique_ids = []
            if enemy_deck:
                last_page = enemy_deck[-1]
                for enemy in last_page.get("svts", []):
                    enemy_unique_ids.append(enemy.get("uniqueId", 0))

            # Parse drop items
            drop_items = []
            for page in enemy_deck:
                for enemy in page.get("svts", []):
                    for drop_info in enemy.get("dropInfos", []):
                        drop_items.append(DropItem(
                            object_id=drop_info.get("objectId", 0),
                            original_num=drop_info.get("originalNum", 0),
                            num=drop_info.get("num", 0),
                        ))

            # Get current AP
            updated = cache.get("updated", {})
            user_game = updated.get("userGame", [{}])[0]
            current_ap = user_game.get("actPoint", 0)

            return BattleSetupResult(
                success=True,
                battle_id=battle_id,
                quest_id=quest_id,
                quest_phase=quest_phase,
                enemy_deck_pages=enemy_deck_pages,
                enemy_unique_ids=enemy_unique_ids,
                my_deck_svt_count=my_deck_svt_count,
                drop_items=drop_items,
                current_ap=current_ap,
            )

        except Exception as e:
            return BattleSetupResult(
                success=False,
                error_message=str(e),
            )

    def battle_result(
        self,
        setup_result: BattleSetupResult,
        user_id: int,
        custom_logs: str = None,
    ) -> BattleResultResponse:
        """
        Submit battle result.

        The battle result payload is automatically encrypted using CatGame5.

        Args:
            setup_result: Result from battle_setup
            user_id: Player's user ID
            custom_logs: Custom command card logs (e.g., "1C1D1B2C2D2B").
                         If None, random logs will be generated.
                         Format: Each card is 2 chars - servant number (1-3) + card type (B/C/D)
                         - B = Arts (blue)
                         - C = Buster (red)
                         - D = Quick (green)
                         Must have 3 cards per wave (e.g., 3 waves = 9 cards = 18 chars)

        Returns:
            BattleResultResponse with friendship updates
        """
        try:
            # Create encrypted battle result
            encrypted_result = self._create_battle_result(
                battle_id=setup_result.battle_id,
                user_id=user_id,
                enemy_deck_pages=setup_result.enemy_deck_pages,
                enemy_unique_ids=setup_result.enemy_unique_ids,
                my_deck_svt_count=setup_result.my_deck_svt_count,
                custom_logs=custom_logs,
            )

            data = self.client.create_form_data({
                "result": encrypted_result,
            })

            response = self.client.post("/battle/result", data, "Battle Result")

            # Parse friendship updates
            cache = response.get("cache", {})
            updated = cache.get("updated", {})
            svt_collection = updated.get("userSvtCollection", [])

            friendship_updates = []
            for svt in svt_collection:
                friendship_updates.append(FriendshipUpdate(
                    svt_id=svt.get("svtId", 0),
                    friendship_rank=svt.get("friendshipRank", 0),
                    friendship=svt.get("friendship", 0),
                ))

            return BattleResultResponse(
                success=True,
                friendship_updates=friendship_updates,
            )

        except Exception as e:
            return BattleResultResponse(
                success=False,
                error_message=str(e),
            )

    def _create_battle_result(
        self,
        battle_id: int,
        user_id: int,
        enemy_deck_pages: int,
        enemy_unique_ids: list,
        my_deck_svt_count: int,
        custom_logs: str = None,
    ) -> str:
        """
        Create encrypted battle result payload.

        Args:
            battle_id: Battle ID from setup
            user_id: Player's user ID
            enemy_deck_pages: Number of enemy deck pages/waves
            enemy_unique_ids: List of enemy unique IDs from last wave
            my_deck_svt_count: Number of servants in player's deck
            custom_logs: Custom command card logs, or None for random

        Returns:
            Base64-encoded encrypted battle result
        """
        # Generate or use custom battle logs
        if custom_logs:
            logs = custom_logs
        else:
            logs = self._generate_battle_logs(enemy_deck_pages, my_deck_svt_count)

        # Generate dt (dead targets) string
        dt = "".join(f"u{uid}" for uid in enemy_unique_ids)

        # Create action JSON string
        action = f'{{"logs":"{logs}","dt":"{dt}","hd":"","data":""}}'

        # Create usedTurnList (more realistic: [0, 0, ..., 1])
        # All waves except the last are cleared in 0 turns (same turn)
        # Only the last wave counts as 1 turn
        used_turn_list = [0] * (enemy_deck_pages - 1) + [1] if enemy_deck_pages > 0 else [1]

        # Build msgpack payload
        battle_status = calc_battle_status(user_id, battle_id)

        payload = {
            "battleId": battle_id,
            "battleResult": 1,
            "winResult": 1,
            "scores": "",
            "action": action,
            "raidResult": "[]",
            "superBossResult": "[]",
            "elapsedTurn": 1,
            "recordType": 1,
            "recordValueJson": {
                "turnMaxDamage": 0,
                "knockdownNum": 0,
                "totalDamageToAliveEnemy": 0,
            },
            "tdPlayed": "[]",
            "usedEquipSkillList": {},
            "svtCommonFlagList": {},
            "skillShiftUniqueIds": [],
            "skillShiftNpcSvtIds": [],
            "calledEnemyUniqueIds": [],
            "aliveUniqueIds": [],
            "battleStatus": battle_status,
            "voicePlayedList": "[]",
            "usedTurnList": used_turn_list,
        }

        # Pack to msgpack and compress
        packed = msgpack.packb(payload)
        compressed = gzip.compress(packed)

        # Encrypt with CatGame5
        return cat_game5(compressed)

    def _generate_battle_logs(self, enemy_deck_pages: int, my_deck_svt_count: int) -> str:
        """
        Generate fake battle command card logs.

        Args:
            enemy_deck_pages: Number of battle waves
            my_deck_svt_count: Number of servants (affects available cards)

        Returns:
            Battle logs string (e.g., "1B2C3D1C2B3C")
        """
        # Limit to 3 servants max for card selection
        svt_count = min(my_deck_svt_count, 3)
        available_cards = BATTLE_LOGS_LIST[:svt_count * 3]

        logs = ""
        for _ in range(enemy_deck_pages):
            # Select 3 random command cards per wave
            for _ in range(3):
                logs += random.choice(available_cards)

        return logs
