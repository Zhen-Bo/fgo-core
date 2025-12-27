"""Item service for AP recovery."""

from fgo_sdk.client.fgo_client import FgoClient
from fgo_sdk.models.battle_data import RecoveryResult


class ItemService:
    """Service for item-related operations."""

    # Apple type constants
    APPLE_QUARTZ = 1      # Saint Quartz (彩蘋果)
    APPLE_GOLDEN = 2      # Golden Apple (金蘋果)
    APPLE_SILVER = 3      # Silver Apple (銀蘋果)
    APPLE_BRONZE = 4      # Bronze Apple (銅蘋果)

    def __init__(self, client: FgoClient):
        self.client = client

    def recover_ap(self, apple_type: int = APPLE_GOLDEN, num: int = 1) -> RecoveryResult:
        """
        Recover AP using apple items.

        Args:
            apple_type: Type of apple to use
                - 1: Saint Quartz (彩蘋果)
                - 2: Golden Apple (金蘋果) [default]
                - 3: Silver Apple (銀蘋果)
                - 4: Bronze Apple (銅蘋果)
            num: Number of apples to use (default: 1)

        Returns:
            RecoveryResult with current AP after recovery
        """
        try:
            data = self.client.create_form_data({
                "num": str(num),
                "recoverId": str(apple_type),
            })

            response = self.client.post("/item/recover", data, "AP Recovery")

            # Parse response
            cache = response.get("cache", {})
            updated = cache.get("updated", {})
            user_game = updated.get("userGame", [{}])[0]

            current_ap = user_game.get("actPoint", 0)
            act_recover_at = user_game.get("actRecoverAt", 0)

            return RecoveryResult(
                success=True,
                current_ap=current_ap,
                act_recover_at=act_recover_at,
                apple_type=apple_type,
            )

        except Exception as e:
            return RecoveryResult(
                success=False,
                error_message=str(e),
                apple_type=apple_type,
            )
