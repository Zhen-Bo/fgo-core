"""Gacha service for drawing from gacha pools."""

import json
from dataclasses import dataclass
from typing import List, Optional

from fgo_sdk.client.fgo_client import FgoClient
from fgo_sdk.models.player_data import GachaObtainItem
from fgo_sdk.utils.wiki_api import search_wiki_svt_or_item


@dataclass
class GachaResult:
    """Result of gacha draw operation."""

    success: bool
    items: List[GachaObtainItem]
    error_message: Optional[str] = None


class GachaService:
    """
    Service for handling gacha operations.

    This service provides low-level gacha API calls. Decision logic
    (e.g., which pool to draw, free draw availability checks) should
    be handled by the application layer.

    Example usage:
        # SDK layer: get time-filtered open gachas
        open_gachas = get_open_gachas(gacha_data)

        # Application layer: filter by user conditions
        visible_gachas = filter_visible_gachas(open_gachas, ...)
        selected = visible_gachas[0]  # User/app selects

        # SDK just executes the draw
        result = gacha_service.draw(
            gacha_id=selected.gacha_id,
            gacha_sub_id=selected.gacha_sub_id,
            num=10
        )
    """

    def __init__(self, client: FgoClient, wiki_api_url: str):
        self.client = client
        self.wiki_api_url = wiki_api_url

    def draw(
        self,
        gacha_id: int,
        gacha_sub_id: int,
        num: int = 10,
        story_adjust_ids: Optional[List[int]] = None,
    ) -> GachaResult:
        """
        Draw from a gacha pool.

        This is the generic draw method that works with any gacha pool.
        The application layer is responsible for:
        - Determining which pool to draw from
        - Checking if free draws are available
        - Validating draw conditions
        - Calculating story_adjust_ids for Story Summon pools

        Args:
            gacha_id: The main gacha pool ID (e.g., 1 for friend point)
            gacha_sub_id: The specific sub-pool ID
            num: Number of draws (default: 10)
            story_adjust_ids: List of story adjust IDs based on cleared quests
                (required for Story Summon gacha 21001)

        Returns:
            GachaResult with obtained items
        """
        try:
            raw_items = self._send_draw_request(
                gacha_id, gacha_sub_id, num, story_adjust_ids
            )
            obtain_items = self._parse_gacha_items(raw_items)

            return GachaResult(
                success=True,
                items=obtain_items,
            )
        except Exception as e:
            return GachaResult(
                success=False,
                items=[],
                error_message=str(e),
            )

    def _send_draw_request(
        self,
        gacha_id: int,
        gacha_sub_id: int,
        num: int,
        story_adjust_ids: Optional[List[int]] = None,
    ) -> List[dict]:
        """
        Execute gacha draw request.

        Args:
            gacha_id: The main gacha pool ID
            gacha_sub_id: The specific sub-pool ID
            num: Number of draws
            story_adjust_ids: List of story adjust IDs for Story Summon gacha

        Returns:
            List of raw gacha item dictionaries from the response
        """
        # Get basic form data for values (but we'll reorder manually)
        basic_data = self.client.create_form_data()

        # Build request with EXACT parameter order matching successful request:
        # storyAdjustIds, selectBonusList, userId, authKey, appVer, dateVer,
        # lastAccessTime, verCode, idempotencyKey, gachaId, num, ticketItemId,
        # shopIdIndex, gachaSubId, dataVer, authCode
        data = {
            'storyAdjustIds': json.dumps(story_adjust_ids or []),
            'selectBonusList': '',
            'userId': basic_data['userId'],
            'authKey': basic_data['authKey'],
            'appVer': basic_data['appVer'],
            'dateVer': basic_data['dateVer'],
            'lastAccessTime': basic_data['lastAccessTime'],
            'verCode': basic_data['verCode'],
            'idempotencyKey': basic_data['idempotencyKey'],
            'gachaId': gacha_id,
            'num': num,
            'ticketItemId': 0,
            'shopIdIndex': 1,
            'gachaSubId': gacha_sub_id,
            'dataVer': basic_data['dataVer'],
            # authCode will be added by post()
        }

        response_data = self.client.post(
            "/gacha/draw",
            data,
            f"抽卡 (gacha:{gacha_id}, sub:{gacha_sub_id})",
        )
        return response_data['response'][0]['success']['gachaInfos']

    def _parse_gacha_items(self, raw_items: List[dict]) -> List[GachaObtainItem]:
        """
        Parse raw gacha response into GachaObtainItem list.

        Args:
            raw_items: Raw item dictionaries from gacha response

        Returns:
            List of parsed GachaObtainItem objects
        """
        obtain_items: List[GachaObtainItem] = []

        for item in raw_items:
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

        return obtain_items
