from dataclasses import dataclass
from typing import List, Optional

from fgo_sdk.client.fgo_client import FgoClient
from fgo_sdk.models.shop_data import WikiShopItem
from fgo_sdk.models.player_data import PlayerInfo, PlayerOwnedItem, UserShopItem
from fgo_sdk.utils.time_tool import get_used_act_amount


@dataclass
class PurchaseResult:
    """Result of a purchase operation."""
    success: bool
    item_name: str
    quantity: int
    error_message: Optional[str] = None


class ShopService:
    """Service for handling shop operations."""

    def __init__(self, client: FgoClient):
        self.client = client

    def buy_blue_apple(self, player_info: PlayerInfo, player_item: PlayerOwnedItem) -> Optional[PurchaseResult]:
        """
        Purchase blue apples using blue apple saplings.

        Returns:
            PurchaseResult if purchase was attempted, None if conditions not met
        """
        if player_item.blue_apple_sapling < 1:
            return PurchaseResult(
                success=False,
                item_name="青銅蘋果",
                quantity=0,
                error_message="青銅樹苗不足"
            )

        act_now = player_info.act_max - get_used_act_amount(player_info.act_full_recover_time)
        if act_now >= 40:
            available_buy_count = int(act_now / 40)
            buy_count = (
                available_buy_count
                if player_item.blue_apple_sapling >= available_buy_count
                else player_item.blue_apple_sapling
            )

            return self._purchase_item("13000000", buy_count, "青銅蘋果")

        return None

    def buy_summon_tickets(
        self,
        player_item: PlayerOwnedItem,
        user_shop: List[UserShopItem],
        tick_data: List[WikiShopItem]
    ) -> List[PurchaseResult]:
        """
        Purchase summon tickets from the shop.

        Returns:
            List of PurchaseResult for each purchase attempt
        """
        results = []
        user_shop_map = {item.shopId: item.num for item in user_shop}

        for item in tick_data:
            shop_id = item.baseShopId
            limit_num = item.limitNum
            price = item.cost.amount
            name = item.detail.replace('\n', ' ')

            purchased_num = user_shop_map.get(shop_id, 0)
            remaining_num = limit_num - purchased_num

            if remaining_num <= 0:
                continue

            max_affordable = player_item.mana // price
            if max_affordable == 0:
                results.append(PurchaseResult(
                    success=False,
                    item_name=name,
                    quantity=0,
                    error_message="魔力稜鏡不足"
                ))
                continue

            buy_count = min(remaining_num, max_affordable)
            result = self._purchase_item(str(shop_id), buy_count, name)
            results.append(result)

            if result.success:
                player_item.mana -= buy_count * price

        return results

    def _purchase_item(self, shop_id: str, num: int, name: str) -> PurchaseResult:
        """Execute a purchase request."""
        data = self.client.create_form_data({
            'id': shop_id,
            'num': num,
        })

        try:
            response_data = self.client.post("/shop/purchase", data, f"購買 {name}")

            result = response_data["response"][0]
            if result["nid"] == "purchase":
                res_success = result["success"]
                purchase_name = res_success["purchaseName"]
                purchase_num = res_success["purchaseNum"]

                return PurchaseResult(
                    success=True,
                    item_name=purchase_name,
                    quantity=purchase_num,
                )
            else:
                return PurchaseResult(
                    success=False,
                    item_name=name,
                    quantity=0,
                    error_message=f"nid={result['nid']}"
                )

        except Exception as e:
            return PurchaseResult(
                success=False,
                item_name=name,
                quantity=0,
                error_message=str(e)
            )
