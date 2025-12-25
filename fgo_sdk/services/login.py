from dataclasses import dataclass
from typing import List

from fgo_sdk.client.fgo_client import FgoClient
from fgo_sdk.models.player_data import (
    LoginInfo,
    PlayerData,
    PlayerInfo,
    PlayerOwnedItem,
    UserQuest,
    UserShopItem,
)


@dataclass
class LoginResult:
    """Result of login operation."""
    player_data: PlayerData
    user_quest: List[UserQuest]
    last_free_friend_point_draw: int


class LoginService:
    """Service for handling login operations."""

    def __init__(self, client: FgoClient):
        self.client = client

    def login(self) -> LoginResult:
        """
        Perform login and return parsed player data.

        Returns:
            LoginResult containing player data, user quests, and last FP draw time
        """
        login_data = self.client.get_login_data()
        data = self.client.post("/login/top", login_data.model_dump(exclude_none=True), "登入")

        # Parse login info
        login_info = LoginInfo()
        user_login_data = data["cache"]["updated"]["userLogin"][0]
        login_seq_days = user_login_data["seqLoginCount"]
        login_total_days = user_login_data["totalLoginCount"]

        # Parse player info
        user_game_data = data["cache"]["replaced"]["userGame"][0]
        player_info = PlayerInfo(
            level=user_game_data["lv"],
            name=user_game_data["name"],
            friend_code=user_game_data["friendCode"],
            act_max=user_game_data["actMax"],
            act_full_recover_time=user_game_data["actRecoverAt"],
            seq_login_days=login_seq_days,
            total_login_days=login_total_days,
        )

        # Parse owned items
        player_owned_item = PlayerOwnedItem()
        player_owned_item.quartz = user_game_data["stone"]
        player_owned_item.qp = user_game_data["qp"]
        player_owned_item.friend_point = data["cache"]["replaced"]["tblUserGame"][0]["friendPoint"]
        player_owned_item.mana = user_game_data["mana"]

        item_map = {
            16: "quartz_fragments",
            100: "golden_apple",
            101: "silver_apple",
            102: "bronze_apple",
            103: "blue_apple_sapling",
            104: "blue_apple",
            4001: "ticket",
            7999: "holy_grail",
        }

        for item in data["cache"]["replaced"]["userItem"]:
            item_id = item["itemId"]
            if item_id in item_map:
                setattr(player_owned_item, item_map[item_id], item["num"])

        # Build full item inventory
        user_items: dict[int, int] = {}
        for item in data["cache"]["replaced"]["userItem"]:
            user_items[item["itemId"]] = item["num"]

        # Parse user shop
        user_shop = []
        if "userShop" in data["cache"]["updated"]:
            for item in data["cache"]["updated"]["userShop"]:
                user_shop.append(UserShopItem(shopId=item["shopId"], num=item["num"]))

        # Parse last free FP draw time
        try:
            last_free_friend_point_draw = data['cache']['replaced']['userGacha'][0]['freeDrawAt']
        except Exception:
            last_free_friend_point_draw = 0

        # Parse user quests
        user_quest = []
        for quest_info in data['cache']['replaced'].get('userQuest', []):
            user_quest.append(
                UserQuest(
                    user_id=quest_info['userId'],
                    quest_id=quest_info['questId'],
                    quest_phase=quest_info['questPhase'],
                    clear_num=quest_info['clearNum'],
                    is_eternal_open=quest_info['isEternalOpen'],
                    expire_at=quest_info['expireAt'],
                    challenge_num=quest_info['challengeNum'],
                    is_new=quest_info['isNew'],
                    last_started_at=quest_info['lastStartedAt'],
                    status=quest_info['status'],
                    updated_at=quest_info['updatedAt'],
                    created_at=quest_info['createdAt'],
                )
            )

        player_data = PlayerData(
            login_info=login_info,
            player_info=player_info,
            ownedItem=player_owned_item,
            user_shop=user_shop,
            user_items=user_items,
        )

        return LoginResult(
            player_data=player_data,
            user_quest=user_quest,
            last_free_friend_point_draw=last_free_friend_point_draw,
        )
