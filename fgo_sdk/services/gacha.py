"""Gacha service for drawing from gacha pools."""

import warnings
from dataclasses import dataclass
from typing import List, Optional

from fgo_sdk.client.fgo_client import FgoClient
from fgo_sdk.models.player_data import GachaObtainItem, UserQuest
from fgo_sdk.utils.gacha_helper import select_gacha_sub
from fgo_sdk.utils.time_tool import is_free_fp_draw_available
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
        # Application layer determines which pool to draw
        visible_gachas = get_visible_gachas(...)
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
    ) -> GachaResult:
        """
        Draw from a gacha pool.

        This is the generic draw method that works with any gacha pool.
        The application layer is responsible for:
        - Determining which pool to draw from
        - Checking if free draws are available
        - Validating draw conditions

        Args:
            gacha_id: The main gacha pool ID (e.g., 1 for friend point)
            gacha_sub_id: The specific sub-pool ID
            num: Number of draws (default: 10)

        Returns:
            GachaResult with obtained items
        """
        try:
            raw_items = self._send_draw_request(gacha_id, gacha_sub_id, num)
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
    ) -> List[dict]:
        """
        Execute gacha draw request.

        Args:
            gacha_id: The main gacha pool ID
            gacha_sub_id: The specific sub-pool ID
            num: Number of draws

        Returns:
            List of raw gacha item dictionaries from the response
        """
        data = self.client.create_form_data({
            'gachaId': gacha_id,
            'gachaSubId': gacha_sub_id,
            'num': num,
        })

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

    # =========================================================================
    # Deprecated methods - kept for backward compatibility
    # =========================================================================

    def _get_friend_point_gacha_sub_id(
        self,
        user_quest: List[UserQuest],
        gacha_data: List,
    ) -> int:
        """
        Find the appropriate friend point gacha sub ID.

        .. deprecated::
            This method will be removed in a future version.
            Use gacha_helper.select_gacha_sub() directly in application layer.
        """
        warnings.warn(
            "_get_friend_point_gacha_sub_id is deprecated. "
            "Use gacha_helper.select_gacha_sub() in application layer.",
            DeprecationWarning,
            stacklevel=2,
        )
        fp_gacha_subs = [
            g for g in gacha_data
            if g.get('gachaId', g.get('id', 0)) == 1
        ]
        selected = select_gacha_sub(fp_gacha_subs, user_quest, self.wiki_api_url)
        return selected['id'] if selected else -1

    def draw_fp_gacha(
        self,
        last_free_draw: int,
        user_quest: List[UserQuest],
        gacha_data: List,
    ) -> GachaResult:
        """
        Draw from the free friend point gacha.

        .. deprecated::
            This method will be removed in a future version.
            Use draw() method instead. Free draw availability checks
            should be done in the application layer using
            gacha_helper.check_gacha_free_draw() or time_tool.is_free_fp_draw_available().

        Args:
            last_free_draw: Timestamp of last free FP draw
            user_quest: User's quest progress
            gacha_data: Available gacha pool data

        Returns:
            GachaResult with obtained items
        """
        warnings.warn(
            "draw_fp_gacha is deprecated. Use draw() method instead. "
            "Free draw checks should be in application layer.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Decision logic (should be in application layer)
        is_available = is_free_fp_draw_available(last_free_draw)
        if not is_available:
            return GachaResult(
                success=False,
                items=[],
                error_message="今日已經抽過友情池",
            )

        # Selection logic (should be in application layer)
        fp_gacha_subs = [
            g for g in gacha_data
            if g.get('gachaId', g.get('id', 0)) == 1
        ]
        selected = select_gacha_sub(fp_gacha_subs, user_quest, self.wiki_api_url)

        if selected is None:
            return GachaResult(
                success=False,
                items=[],
                error_message="找不到開啟中的友情池",
            )

        # Delegate to the new generic draw method
        return self.draw(
            gacha_id=1,
            gacha_sub_id=selected['id'],
            num=10,
        )
