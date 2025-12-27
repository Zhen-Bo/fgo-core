from dataclasses import dataclass
from typing import Optional

from fgo_sdk.client.fgo_client import FgoClient


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

    def buy_blue_apple(self, num: int) -> PurchaseResult:
        """
        Purchase blue apples using blue apple saplings.

        Args:
            num: Number of blue apples to purchase

        Returns:
            PurchaseResult with success status and quantity
        """
        if num < 1:
            return PurchaseResult(
                success=False,
                item_name="青銅蘋果",
                quantity=0,
                error_message="購買數量必須大於 0"
            )

        return self.purchase_item(13000000, num, "青銅蘋果")

    def purchase_item(self, shop_id: int, num: int, name: str = "") -> PurchaseResult:
        """
        Execute a single shop purchase.

        Args:
            shop_id: Shop item ID
            num: Quantity to purchase (caller is responsible for calculating this)
            name: Item name for logging (optional)

        Returns:
            PurchaseResult with success status and quantity
        """
        data = self.client.create_form_data({
            'id': str(shop_id),
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
