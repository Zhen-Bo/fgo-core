import base64
from dataclasses import dataclass, field
from typing import Dict, List

import msgpack

from fgo_sdk.client.fgo_client import FgoClient
from fgo_sdk.models.player_data import ItemInfo, PresentBox, PresentInfo
from fgo_sdk.utils.wiki_api import search_wiki_svt_or_item


@dataclass
class ReceivedPresent:
    """Information about a received present."""
    item_info: ItemInfo
    quantity: int


@dataclass
class PresentResult:
    """Result of present receiving operation."""
    received_items: List[ReceivedPresent]
    is_all_received: bool
    total_requested: int
    total_received: int


@dataclass
class ExchangeSelectableItem:
    """Information about a selectable item in an exchange ticket."""
    idx: int              # Selection index (1-based, used as itemSelectIdx)
    item_id: int          # The item ID to receive
    item_name: str        # Item name
    item_icon: str        # Item icon URL
    num: int              # Quantity per exchange
    require_num: int      # Number of tickets required


@dataclass
class ExchangeTicketInfo:
    """Information about an exchange ticket in the present box."""
    present_id: int
    object_id: int
    name: str
    quantity: int
    selectable_items: List[ExchangeSelectableItem] = field(default_factory=list)


@dataclass
class ExchangeTicketResult:
    """Result of exchange ticket receiving operation."""
    success: bool
    item_name: str = ""
    quantity: int = 0
    error_message: str = ""


class PresentService:
    """Service for handling present box operations."""

    def __init__(self, client: FgoClient, wiki_api_url: str):
        self.client = client
        self.wiki_api_url = wiki_api_url

    def get_present_box(self) -> PresentBox:
        """Get current present box contents."""
        data = self.client.create_form_data()
        response_data = self.client.post("/present/list", data, "取得禮物箱內容")

        box_info = response_data['cache']['replaced']['userPresentBox']
        return PresentBox(userPresentBox=box_info)

    def receive_presents(self) -> PresentResult:
        """
        Receive presents from the present box.

        Returns:
            PresentResult with received items and status
        """
        box = self.get_present_box()

        # Build search cache for item info
        search_cache = self._get_search_cache(box.userPresentBox)

        # Filter presents to receive (type 2 or specific IDs, excluding exchange tickets)
        extra_need_receive_item_ids: List[int] = []
        need_receive_present = [
            present
            for present in box.userPresentBox
            if (present.giftType == 2 or present.objectId in extra_need_receive_item_ids)
            and not search_cache[present.objectId].is_exchange_ticket
        ]

        if len(need_receive_present) == 0:
            return PresentResult(
                received_items=[],
                is_all_received=True,
                total_requested=0,
                total_received=0,
            )

        # Prepare present IDs for request
        msgpack_data = msgpack.packb([present.presentId for present in need_receive_present])
        present_ids_b64 = base64.b64encode(msgpack_data).decode()

        # Receive presents
        confirm_received_present = self._receive_present(present_ids_b64)

        # Aggregate received items
        for item in confirm_received_present:
            search_cache[item.objectId].num += item.num

        received_items = [
            ReceivedPresent(item_info=item, quantity=item.num)
            for item in search_cache.values()
            if item.num > 0
        ]

        is_all_received = len(need_receive_present) == len(confirm_received_present)

        return PresentResult(
            received_items=received_items,
            is_all_received=is_all_received,
            total_requested=len(need_receive_present),
            total_received=len(confirm_received_present),
        )

    def _receive_present(self, present_ids: str) -> List[PresentInfo]:
        """Execute present receive request."""
        data = self.client.create_form_data({
            'presentIds': present_ids,
            'itemSelectIdx': "0",
            'itemSelectNum': "0",
        })

        response_data = self.client.post("/present/receive", data, "領取禮物")
        return PresentBox(userPresentBox=response_data['cache']['deleted']['userPresentBox']).userPresentBox

    def _get_search_cache(self, data: List[PresentInfo]) -> Dict[int, ItemInfo]:
        """Build cache of item info for presents."""
        cache: Dict[int, ItemInfo] = {}
        for present in data:
            if present.objectId not in cache and present.giftType in [1, 2]:
                cache[present.objectId] = search_wiki_svt_or_item(
                    self.wiki_api_url, present.objectId, present.giftType
                )
        return cache

    def get_exchange_tickets(self) -> List[ExchangeTicketInfo]:
        """
        Get exchange tickets from the present box.

        Returns:
            List of ExchangeTicketInfo containing ticket details and selectable items
        """
        box = self.get_present_box()
        exchange_tickets: List[ExchangeTicketInfo] = []

        for present in box.userPresentBox:
            if present.giftType != 2:
                continue

            item_info = search_wiki_svt_or_item(
                self.wiki_api_url, present.objectId, present.giftType
            )

            if item_info.is_exchange_ticket:
                selectable_items = self._get_exchange_ticket_details(present.objectId)
                exchange_tickets.append(ExchangeTicketInfo(
                    present_id=present.presentId,
                    object_id=present.objectId,
                    name=item_info.name,
                    quantity=present.num,
                    selectable_items=selectable_items,
                ))

        return exchange_tickets

    def _get_exchange_ticket_details(self, item_id: int) -> List[ExchangeSelectableItem]:
        """
        Get selectable items for an exchange ticket from the wiki API.

        Args:
            item_id: The exchange ticket item ID

        Returns:
            List of ExchangeSelectableItem with enriched item info
        """
        import requests

        try:
            # Get exchange ticket data
            response = requests.get(f"{self.wiki_api_url}/nice/JP/item/{item_id}")
            response.raise_for_status()
            ticket_data = response.json()

            item_selects = ticket_data.get('itemSelects', [])
            if not item_selects:
                return []

            # Collect all item IDs we need to look up
            item_ids_to_fetch: List[int] = []
            for select in item_selects:
                for gift in select.get('gifts', []):
                    if gift.get('type') == 'item':
                        item_ids_to_fetch.append(gift['objectId'])

            # Fetch item info for all items
            item_info_cache: Dict[int, Dict] = {}
            for obj_id in set(item_ids_to_fetch):
                try:
                    item_resp = requests.get(f"{self.wiki_api_url}/nice/JP/item/{obj_id}")
                    if item_resp.status_code == 200:
                        item_info_cache[obj_id] = item_resp.json()
                except Exception:
                    pass

            # Build selectable items list
            selectable_items: List[ExchangeSelectableItem] = []
            for select in item_selects:
                idx = select.get('idx', 0)
                require_num = select.get('requireNum', 1)

                for gift in select.get('gifts', []):
                    if gift.get('type') != 'item':
                        continue

                    obj_id = gift['objectId']
                    num = gift.get('num', 1)
                    cached_info = item_info_cache.get(obj_id, {})

                    selectable_items.append(ExchangeSelectableItem(
                        idx=idx,
                        item_id=obj_id,
                        item_name=cached_info.get('name', f'Unknown Item ({obj_id})'),
                        item_icon=cached_info.get('icon', ''),
                        num=num,
                        require_num=require_num,
                    ))

            return selectable_items

        except Exception:
            return []

    def receive_exchange_ticket(
        self,
        present_id: int,
        item_select_idx: int,
        item_select_num: int,
    ) -> ExchangeTicketResult:
        """
        Receive an exchange ticket with a specific item selection.

        Args:
            present_id: The present ID of the exchange ticket
            item_select_idx: The index of the selected item (1-based)
            item_select_num: The quantity to exchange

        Returns:
            ExchangeTicketResult with success status and received item info
        """
        if item_select_idx < 1:
            return ExchangeTicketResult(
                success=False,
                error_message="item_select_idx must be >= 1"
            )

        if item_select_num < 1:
            return ExchangeTicketResult(
                success=False,
                error_message="item_select_num must be >= 1"
            )

        msgpack_data = msgpack.packb([present_id])
        present_ids_b64 = base64.b64encode(msgpack_data).decode()

        data = self.client.create_form_data({
            'presentIds': present_ids_b64,
            'itemSelectIdx': str(item_select_idx),
            'itemSelectNum': str(item_select_num),
        })

        try:
            response_data = self.client.post("/present/receive", data, "領取交換券")
            deleted_presents = response_data['cache']['deleted'].get('userPresentBox', [])

            if deleted_presents:
                return ExchangeTicketResult(
                    success=True,
                    quantity=item_select_num,
                )
            else:
                return ExchangeTicketResult(
                    success=False,
                    error_message="No presents were received"
                )
        except Exception as e:
            return ExchangeTicketResult(
                success=False,
                error_message=str(e)
            )
