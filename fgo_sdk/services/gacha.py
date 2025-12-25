from dataclasses import dataclass
from typing import List, Optional

from fgo_sdk.client.fgo_client import FgoClient
from fgo_sdk.models.player_data import GachaObtainItem, UserQuest
from fgo_sdk.utils.time_tool import is_free_fp_draw_available
from fgo_sdk.utils.wiki_api import search_wiki_svt_or_item
from fgo_sdk.utils.gacha_helper import select_gacha_sub


@dataclass
class GachaResult:
    """Result of gacha draw operation."""
    success: bool
    items: List[GachaObtainItem]
    error_message: Optional[str] = None


class GachaService:
    """Service for handling gacha operations."""

    def __init__(self, client: FgoClient, wiki_api_url: str):
        self.client = client
        self.wiki_api_url = wiki_api_url

    def _get_friend_point_gacha_sub_id(self, user_quest: List[UserQuest], gacha_data: List) -> int:
        """Find the appropriate friend point gacha sub ID."""
        # Filter to FP gacha (gachaId == 1)
        fp_gacha_subs = [g for g in gacha_data if g.get('gachaId', g.get('id', 0)) == 1]

        selected = select_gacha_sub(fp_gacha_subs, user_quest, self.wiki_api_url)
        return selected['id'] if selected else -1

    def _send_draw_friend_gacha_request(self, gacha_sub_id: int) -> List:
        """Execute friend point gacha draw request."""
        data = self.client.create_form_data({
            'gachaId': 1,
            'gachaSubId': gacha_sub_id,
            'num': 10,
        })

        response_data = self.client.post("/gacha/draw", data, f"抽友情池 (id:{gacha_sub_id})")
        return response_data['response'][0]['success']['gachaInfos']

    def draw_fp_gacha(
        self,
        last_free_draw: int,
        user_quest: List[UserQuest],
        gacha_data: List
    ) -> GachaResult:
        """
        Draw from the free friend point gacha.

        Args:
            last_free_draw: Timestamp of last free FP draw
            user_quest: User's quest progress
            gacha_data: Available gacha pool data

        Returns:
            GachaResult with obtained items
        """
        is_available = is_free_fp_draw_available(last_free_draw)

        if not is_available:
            return GachaResult(
                success=False,
                items=[],
                error_message="今日已經抽過友情池"
            )

        gacha_id = self._get_friend_point_gacha_sub_id(user_quest, gacha_data)
        if gacha_id == -1:
            return GachaResult(
                success=False,
                items=[],
                error_message="找不到開啟中的友情池"
            )

        result = self._send_draw_friend_gacha_request(gacha_id)

        obtain_items: List[GachaObtainItem] = []
        for item in result:
            item_info = search_wiki_svt_or_item(
                self.wiki_api_url, item['objectId'], item['type']
            )
            obtain_items.append(
                GachaObtainItem(
                    **item_info.model_dump(exclude_defaults=True),
                    num=item['num'],
                    sell_qp=item['sellQp'],
                    sell_mana=item['sellMana'],
                )
            )

        return GachaResult(
            success=True,
            items=obtain_items,
        )
