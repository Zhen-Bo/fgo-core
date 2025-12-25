from typing import Dict, List

from pydantic import BaseModel


class ItemInfo(BaseModel):
    name: str
    num: int = 0
    thumbnail: str | None = None
    is_exchange_ticket: bool = False


class LoginInfo(BaseModel):
    bonus_message: str = ""
    bonus_items: list[ItemInfo] = []
    event_title: str = ""
    event_desc: str = ""
    event_items: list[ItemInfo] = []
    friend_point_get_this_login: int = 0


class PlayerInfo(BaseModel):
    level: int
    name: str
    friend_code: str
    act_max: int
    act_full_recover_time: int
    seq_login_days: int = 0
    total_login_days: int = 0


class PlayerOwnedItem(BaseModel):
    qp: int = 0
    quartz: int = 0
    quartz_fragments: int = 0
    ticket: int = 0
    golden_apple: int = 0
    silver_apple: int = 0
    bronze_apple: int = 0
    blue_apple_sapling: int = 0
    blue_apple: int = 0
    holy_grail: int = 0
    friend_point: int = 0
    mana: int = 0


class UserShopItem(BaseModel):
    shopId: int
    num: int


class PlayerData(BaseModel):
    login_info: LoginInfo
    player_info: PlayerInfo
    ownedItem: PlayerOwnedItem
    user_shop: List[UserShopItem] = []
    user_items: Dict[int, int] = {}  # Full item inventory: {item_id: quantity}


class PresentInfo(BaseModel):
    receiveUserId: int
    presentId: int
    messageRefType: int
    messageId: int
    message: str
    fromType: int
    giftType: int
    objectId: int
    num: int
    limitCount: int
    lv: int
    flag: int
    updatedAt: int
    createdAt: int


class PresentBox(BaseModel):
    userPresentBox: List[PresentInfo] = []


class GachaObtainItem(ItemInfo):
    sell_qp: int
    sell_mana: int


class UserQuest(BaseModel):
    user_id: int
    quest_id: int
    quest_phase: int
    clear_num: int
    is_eternal_open: bool
    expire_at: int
    challenge_num: int
    is_new: bool
    last_started_at: int
    status: int
    updated_at: int
    created_at: int
