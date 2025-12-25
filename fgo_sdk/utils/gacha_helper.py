"""
Gacha helper utilities for filtering and selecting visible gacha pools.

This module provides functions to:
- Filter gacha pools based on time and user conditions
- Select appropriate gachaSub based on release conditions
- Check free draw availability
- Fetch gacha data from Atlas Academy with retry support
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Dict, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from fgo_sdk.models.player_data import UserQuest
from fgo_sdk.utils.time_tool import get_timestamp, is_free_fp_draw_available


# Default URLs for gacha data
GACHA_SUB_DATA_URL = "https://git.atlasacademy.io/atlasacademy/fgo-game-data/raw/branch/JP/master/mstGachaSub.json"
GACHA_DATA_URL = "https://git.atlasacademy.io/atlasacademy/fgo-game-data/raw/branch/JP/master/mstGacha.json"


def _create_retry_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: Tuple[int, ...] = (500, 502, 503, 504),
) -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_gacha_sub_data(
    url: str = GACHA_SUB_DATA_URL,
    retries: int = 3,
    timeout: int = 30,
) -> List[dict]:
    """
    Fetch mstGachaSub.json from Atlas Academy git with retry support.

    This is the lightweight gacha sub-pool data (~500 entries).

    Args:
        url: URL to fetch from (defaults to Atlas Academy git)
        retries: Number of retry attempts
        timeout: Request timeout in seconds

    Returns:
        List of gacha sub dictionaries

    Raises:
        requests.exceptions.RequestException: If all retries fail
    """
    session = _create_retry_session(retries=retries, timeout=timeout)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_gacha_data(
    url: str = GACHA_DATA_URL,
    retries: int = 3,
    timeout: int = 30,
) -> List[dict]:
    """
    Fetch mstGacha.json from Atlas Academy git with retry support.

    This contains gacha metadata (name, type, freeDrawFlag, etc.).

    Args:
        url: URL to fetch from (defaults to Atlas Academy git)
        retries: Number of retry attempts
        timeout: Request timeout in seconds

    Returns:
        List of gacha dictionaries

    Raises:
        requests.exceptions.RequestException: If all retries fail
    """
    session = _create_retry_session(retries=retries, timeout=timeout)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_combined_gacha_data(
    retries: int = 3,
    timeout: int = 30,
) -> List[dict]:
    """
    Fetch and combine mstGacha and mstGachaSub data.

    Merges gacha metadata (name, type, freeDrawFlag) with sub-pool data
    (openedAt, closedAt, priority, commonReleaseId).

    Args:
        retries: Number of retry attempts
        timeout: Request timeout in seconds

    Returns:
        List of combined gacha sub dictionaries with full metadata
    """
    gacha_data = fetch_gacha_data(retries=retries, timeout=timeout)
    gacha_sub_data = fetch_gacha_sub_data(retries=retries, timeout=timeout)

    # Build gacha lookup by id
    gacha_map: Dict[int, dict] = {g['id']: g for g in gacha_data}

    # Merge sub data with parent gacha data
    combined: List[dict] = []
    for sub in gacha_sub_data:
        gacha_id = sub.get('gachaId', 0)
        parent = gacha_map.get(gacha_id, {})

        combined.append({
            # From mstGachaSub
            'id': sub.get('id', 0),
            'gachaId': gacha_id,
            'priority': sub.get('priority', 0),
            'imageId': sub.get('imageId', 0),
            'openedAt': sub.get('openedAt', 0),
            'closedAt': sub.get('closedAt', 0),
            'commonReleaseId': sub.get('commonReleaseId', 0),
            # From mstGacha
            'name': parent.get('name', ''),
            'type': parent.get('type', 0),
            'freeDrawFlag': parent.get('freeDrawFlag', 0),
            'detailUrl': parent.get('detailUrl', ''),
        })

    return combined


@dataclass
class GachaSubInfo:
    """Information about a gacha sub-pool."""
    id: int
    priority: int
    open_at: int
    close_at: int
    image_id: int


@dataclass
class VisibleGacha:
    """Visible gacha pool information for display."""
    gacha_id: int
    gacha_sub_id: int
    name: str
    type: str  # 'friendPoint', 'stone', 'chargeStone', 'payGacha'
    image_id: int
    open_at: int
    close_at: int
    free_draw_flag: bool = False
    free_draw_available: bool = False
    detail_url: str = ""


@dataclass
class UserGachaInfo:
    """User's gacha draw history."""
    gacha_id: int
    free_draw_at: int = 0
    is_new_gacha: bool = True


@lru_cache(maxsize=128)
def _fetch_common_release(api_url: str, common_release_id: int) -> List[dict]:
    """Fetch common release conditions from wiki API."""
    try:
        response = requests.get(f"{api_url}/nice/JP/common-release/{common_release_id}")
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


def _check_release_conditions(
    common_release_id: int,
    user_quest: List[UserQuest],
    wiki_api_url: str,
) -> bool:
    """
    Check if user meets release conditions for a gachaSub.

    Args:
        common_release_id: The common release ID to check
        user_quest: User's quest progress list
        wiki_api_url: Base URL for the wiki API

    Returns:
        True if conditions are met or no conditions exist
    """
    if common_release_id == 0:
        return True

    conditions = _fetch_common_release(wiki_api_url, common_release_id)
    if not conditions:
        return True

    user_quest_map = {q.quest_id: q for q in user_quest}

    for cond in conditions:
        cond_type = cond.get("condType")
        cond_id = cond.get("condId")

        quest = user_quest_map.get(cond_id)
        is_cleared = quest is not None and quest.clear_num > 0

        if cond_type == "questClear":
            if not is_cleared:
                return False
        elif cond_type == "questNotClear":
            if is_cleared:
                return False

    return True


def select_gacha_sub(
    gacha_subs: List[dict],
    user_quest: List[UserQuest],
    wiki_api_url: str,
    current_time: Optional[int] = None,
) -> Optional[dict]:
    """
    Select the appropriate gachaSub from a list based on user conditions.

    Selection logic:
    1. Filter by time (openedAt < now < closedAt)
    2. Sort by priority (descending)
    3. Check release conditions
    4. Return first matching gachaSub

    Args:
        gacha_subs: List of gachaSub dictionaries
        user_quest: User's quest progress list
        wiki_api_url: Base URL for the wiki API
        current_time: Current timestamp (optional, defaults to now)

    Returns:
        The selected gachaSub dict, or None if no valid sub found
    """
    if current_time is None:
        current_time = get_timestamp()

    # Filter active gachaSubs
    active_subs = [
        sub for sub in gacha_subs
        if sub.get('openedAt', 0) < current_time < sub.get('closedAt', 0)
    ]

    if not active_subs:
        return None

    # Sort by priority (descending)
    sorted_subs = sorted(active_subs, key=lambda x: x.get('priority', 0), reverse=True)

    # Find first matching based on conditions
    for sub in sorted_subs:
        common_release_id = sub.get('condGroup', 0)
        if _check_release_conditions(common_release_id, user_quest, wiki_api_url):
            return sub

    return None


def get_visible_gachas(
    gacha_data: List[dict],
    user_gacha: List[dict],
    user_quest: List[UserQuest],
    wiki_api_url: str,
    gacha_ids: Optional[List[int]] = None,
    current_time: Optional[int] = None,
) -> List[VisibleGacha]:
    """
    Get list of visible gacha pools for the user.

    This function filters gacha pools based on:
    - Time availability (openedAt/closedAt)
    - User's quest progress (release conditions)
    - Optional gacha ID filter

    Args:
        gacha_data: Full gacha data from Atlas API (/export/JP/nice_gacha.json)
        user_gacha: User's gacha data from login response
        user_quest: User's quest progress list
        wiki_api_url: Base URL for the wiki API
        gacha_ids: Optional list of gacha IDs to filter (if None, returns all visible)
        current_time: Current timestamp (optional, defaults to now)

    Returns:
        List of VisibleGacha objects representing pools the user can draw from
    """
    if current_time is None:
        current_time = get_timestamp()

    # Build user gacha lookup
    user_gacha_map: Dict[int, dict] = {
        g.get('gachaId', 0): g for g in user_gacha
    }

    # Group gacha data by gachaId
    gacha_by_id: Dict[int, List[dict]] = {}
    for gacha in gacha_data:
        gacha_id = gacha.get('id', 0)
        if gacha_id not in gacha_by_id:
            gacha_by_id[gacha_id] = []
        gacha_by_id[gacha_id].append(gacha)

    # Filter by requested IDs if provided
    target_ids = gacha_ids if gacha_ids else list(gacha_by_id.keys())

    visible_gachas: List[VisibleGacha] = []

    for gacha_id in target_ids:
        if gacha_id not in gacha_by_id:
            continue

        gacha_subs = gacha_by_id[gacha_id]

        # Select appropriate sub-pool
        selected_sub = select_gacha_sub(
            gacha_subs, user_quest, wiki_api_url, current_time
        )

        if selected_sub is None:
            continue

        # Get user's draw history for this gacha
        user_gacha_info = user_gacha_map.get(gacha_id, {})
        free_draw_at = user_gacha_info.get('freeDrawAt', 0)

        # Determine gacha type
        gacha_type = selected_sub.get('type', 'unknown')

        # Check free draw availability
        free_draw_flag = selected_sub.get('freeDrawFlag', 0) == 1
        free_draw_available = False
        if free_draw_flag and free_draw_at > 0:
            free_draw_available = is_free_fp_draw_available(free_draw_at)
        elif free_draw_flag and free_draw_at == 0:
            # Never drawn before, free draw is available
            free_draw_available = True

        visible_gachas.append(VisibleGacha(
            gacha_id=gacha_id,
            gacha_sub_id=selected_sub.get('id', 0),
            name=selected_sub.get('name', ''),
            type=gacha_type,
            image_id=selected_sub.get('imageId', 0),
            open_at=selected_sub.get('openedAt', 0),
            close_at=selected_sub.get('closedAt', 0),
            free_draw_flag=free_draw_flag,
            free_draw_available=free_draw_available,
            detail_url=selected_sub.get('detailUrl', ''),
        ))

    return visible_gachas


def get_drawable_gacha_ids(
    gacha_data: List[dict],
    current_time: Optional[int] = None,
) -> List[int]:
    """
    Get list of gacha IDs that are currently open for drawing.

    This is a lightweight function that only checks time availability,
    not release conditions. Useful for initial filtering before
    calling get_visible_gachas.

    Args:
        gacha_data: Full gacha data from Atlas API
        current_time: Current timestamp (optional, defaults to now)

    Returns:
        List of unique gacha IDs that are currently open
    """
    if current_time is None:
        current_time = get_timestamp()

    active_ids: set = set()

    for gacha in gacha_data:
        if gacha.get('openedAt', 0) < current_time < gacha.get('closedAt', 0):
            active_ids.add(gacha.get('id', 0))

    return list(active_ids)


def check_gacha_free_draw(
    gacha_id: int,
    gacha_data: List[dict],
    user_gacha: List[dict],
    current_time: Optional[int] = None,
) -> bool:
    """
    Check if free draw is available for a specific gacha.

    Args:
        gacha_id: The gacha ID to check
        gacha_data: Full gacha data from Atlas API
        user_gacha: User's gacha data from login response
        current_time: Current timestamp (optional, defaults to now)

    Returns:
        True if free draw is available
    """
    if current_time is None:
        current_time = get_timestamp()

    # Find the gacha in data
    target_gacha = None
    for gacha in gacha_data:
        if gacha.get('id', 0) == gacha_id:
            if gacha.get('openedAt', 0) < current_time < gacha.get('closedAt', 0):
                target_gacha = gacha
                break

    if target_gacha is None:
        return False

    # Check if this gacha supports free draws
    if target_gacha.get('freeDrawFlag', 0) != 1:
        return False

    # Find user's last draw time
    user_gacha_map = {g.get('gachaId', 0): g for g in user_gacha}
    user_info = user_gacha_map.get(gacha_id, {})
    free_draw_at = user_info.get('freeDrawAt', 0)

    if free_draw_at == 0:
        return True

    return is_free_fp_draw_available(free_draw_at)
