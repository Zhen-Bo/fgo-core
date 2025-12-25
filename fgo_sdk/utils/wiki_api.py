from functools import lru_cache

import requests

from fgo_sdk.models.player_data import ItemInfo


@lru_cache(maxsize=256)
def search_wiki_svt_or_item(api_url: str, item_id: int, item_type: int) -> ItemInfo:
    """
    Search for servant or item info from the wiki API.

    Args:
        api_url: Base URL of the wiki API
        item_id: ID of the item/servant
        item_type: Type of the item (1=servant, 11=CC, other=item)

    Returns:
        ItemInfo with name, thumbnail, and exchange ticket status

    Note:
        - For servant (type=1) and CC (type=11): Uses /basic endpoint (lighter response)
        - For item (type=2): Uses /nice endpoint (required for itemSelects field)
    """
    try:
        if item_type == 1:
            # Servant or Equip - use /basic endpoint
            response = requests.get(f"{api_url}/basic/JP/servant/{item_id}")
            response.raise_for_status()
            data = response.json()
            return ItemInfo(
                name=data['name'],
                thumbnail=data['face'],
                is_exchange_ticket=False,
            )
        elif item_type == 11:
            # Command Code - use /basic endpoint
            response = requests.get(f"{api_url}/basic/JP/CC/{item_id}")
            response.raise_for_status()
            data = response.json()
            return ItemInfo(
                name=data['name'],
                thumbnail=data['face'],
                is_exchange_ticket=False,
            )
        else:
            # Item - must use /nice endpoint for itemSelects field
            response = requests.get(f"{api_url}/nice/JP/item/{item_id}")
            response.raise_for_status()
            data = response.json()
            return ItemInfo(
                name=data['name'],
                thumbnail=data['icon'],
                is_exchange_ticket=len(data.get('itemSelects', [])) > 0,
            )
    except requests.exceptions.HTTPError:
        raise NameError("找不到物品或從者")
    except Exception:
        raise Exception("取得物品縮圖時遇到未知錯誤")
