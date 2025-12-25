from typing import List

from pydantic import BaseModel


class WikiShopCost(BaseModel):
    amount: int


class WikiShopItem(BaseModel):
    id: int
    baseShopId: int
    shopType: str
    name: str
    detail: str
    payType: str
    cost: WikiShopCost
    purchaseType: str
    targetIds: List[int]
    setNum: int
    limitNum: int
    openedAt: int
    closedAt: int
