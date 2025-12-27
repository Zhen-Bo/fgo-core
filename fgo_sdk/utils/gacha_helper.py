"""
Gacha helper utilities for fetching and basic filtering of gacha pools.

This module provides functions to:
- Fetch gacha data from Atlas Academy
- Filter gacha pools based on time availability (openedAt/closedAt)
- Provide raw gacha data for application layer to process

Note: This module only performs time-based filtering. All condition checking
(questClear, privilegeValid, eventScriptPlay, etc.) should be done by the
application layer (CLI), not the SDK.

Note: This module does not include retry logic. If retry is needed,
the application layer should implement it.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional

import requests

from fgo_sdk.models.gacha_data import GachaType
from fgo_sdk.utils.time_tool import get_timestamp


# Default URLs for gacha data
GACHA_SUB_DATA_URL = "https://git.atlasacademy.io/atlasacademy/fgo-game-data/raw/branch/JP/master/mstGachaSub.json"
GACHA_DATA_URL = "https://git.atlasacademy.io/atlasacademy/fgo-game-data/raw/branch/JP/master/mstGacha.json"


def fetch_gacha_sub_data(
    url: str = GACHA_SUB_DATA_URL,
    timeout: int = 30,
) -> List[dict]:
    """
    Fetch mstGachaSub.json from Atlas Academy git.

    This is the lightweight gacha sub-pool data (~500 entries).

    Args:
        url: URL to fetch from (defaults to Atlas Academy git)
        timeout: Request timeout in seconds

    Returns:
        List of gacha sub dictionaries

    Raises:
        requests.exceptions.RequestException: If request fails
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_gacha_data(
    url: str = GACHA_DATA_URL,
    timeout: int = 30,
) -> List[dict]:
    """
    Fetch mstGacha.json from Atlas Academy git.

    This contains gacha metadata (name, type, freeDrawFlag, etc.).

    Args:
        url: URL to fetch from (defaults to Atlas Academy git)
        timeout: Request timeout in seconds

    Returns:
        List of gacha dictionaries

    Raises:
        requests.exceptions.RequestException: If request fails
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_combined_gacha_data(
    timeout: int = 30,
) -> List[dict]:
    """
    Fetch and combine mstGacha and mstGachaSub data.

    Merges gacha metadata (name, type, freeDrawFlag) with sub-pool data
    (openedAt, closedAt, priority, commonReleaseId).

    Also includes gachas without sub-pools (like Story Summon gachaId=21001),
    which use openedAt/closedAt directly from the main gacha entry.

    Args:
        timeout: Request timeout in seconds

    Returns:
        List of combined gacha dictionaries with full metadata
    """
    gacha_data = fetch_gacha_data(timeout=timeout)
    gacha_sub_data = fetch_gacha_sub_data(timeout=timeout)

    # Build gacha lookup by id
    gacha_map: Dict[int, dict] = {g["id"]: g for g in gacha_data}

    # Track which gacha IDs have sub-pools
    gacha_ids_with_subs: set = set()

    # Merge sub data with parent gacha data
    combined: List[dict] = []
    for sub in gacha_sub_data:
        gacha_id = sub.get("gachaId", 0)
        parent = gacha_map.get(gacha_id, {})
        gacha_ids_with_subs.add(gacha_id)

        combined.append(
            {
                # From mstGachaSub
                "id": sub.get("id", 0),
                "gachaId": gacha_id,
                "priority": sub.get("priority", 0),
                "imageId": sub.get("imageId", 0),
                "openedAt": sub.get("openedAt", 0),
                "closedAt": sub.get("closedAt", 0),
                "commonReleaseId": sub.get("commonReleaseId", 0),
                # From mstGacha
                "name": parent.get("name", ""),
                "type": parent.get("type", 0),
                "freeDrawFlag": parent.get("freeDrawFlag", 0),
                "detailUrl": parent.get("detailUrl", ""),
            }
        )

    # Add gachas without sub-pools (e.g., Story Summon)
    # These use openedAt/closedAt from the main gacha entry
    for gacha in gacha_data:
        gacha_id = gacha.get("id", 0)
        if gacha_id not in gacha_ids_with_subs:
            # Use main gacha id as both gachaId and sub id (id=0 means no sub)
            combined.append(
                {
                    "id": 0,  # No sub-pool, use 0
                    "gachaId": gacha_id,
                    "priority": gacha.get("priority", 0),
                    "imageId": gacha.get("imageId", 0),
                    "openedAt": gacha.get("openedAt", 0),
                    "closedAt": gacha.get("closedAt", 0),
                    "commonReleaseId": 0,  # Main gachas use condQuestId instead
                    "condQuestId": gacha.get("condQuestId", 0),  # Quest condition
                    "condQuestPhase": gacha.get("condQuestPhase", 0),
                    # From mstGacha directly
                    "name": gacha.get("name", ""),
                    "type": gacha.get("type", 0),
                    "freeDrawFlag": gacha.get("freeDrawFlag", 0),
                    "detailUrl": gacha.get("detailUrl", ""),
                }
            )

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
class OpenGacha:
    """
    An open gacha pool (filtered by time only).

    This represents a gacha that is currently open based on openedAt/closedAt.
    Application layer should perform additional filtering (conditions, etc.).
    """

    gacha_id: int
    gacha_sub_id: int
    name: str
    type: GachaType
    image_id: int
    open_at: int
    close_at: int
    priority: int
    common_release_id: int
    cond_quest_id: int
    cond_quest_phase: int
    free_draw_flag: bool
    detail_url: str = ""


# Default timeout for API requests (in seconds)
# Format: (connect_timeout, read_timeout)
DEFAULT_API_TIMEOUT = (10, 15)


def fetch_common_release(
    api_url: str,
    common_release_id: int,
    timeout: int = DEFAULT_API_TIMEOUT,
) -> List[dict]:
    """
    Fetch common release conditions from wiki API.

    This is a data-fetching function. The application layer should
    use this data to check conditions.

    Args:
        api_url: Base URL for the wiki API
        common_release_id: The common release ID to fetch
        timeout: Request timeout in seconds (default: 15)

    Returns:
        List of condition dictionaries from the API
    """
    url = f"{api_url}/nice/JP/common-release/{common_release_id}"
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return []
    except Exception:
        return []


def fetch_gacha_info(
    api_url: str,
    gacha_id: int,
    timeout: int = DEFAULT_API_TIMEOUT,
) -> Optional[dict]:
    """
    Fetch full gacha info from Atlas Academy API.

    Returns the complete gacha data including releaseConditions and storyAdjusts.

    Args:
        api_url: Base URL for the wiki API
        gacha_id: The gacha ID to fetch
        timeout: Request timeout in seconds (default: 15)

    Returns:
        Full gacha data dict, or None if not found
    """
    url = f"{api_url}/nice/JP/gacha/{gacha_id}"
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return None
    except Exception:
        return None


def get_open_gachas(
    gacha_data: List[dict],
    current_time: Optional[int] = None,
) -> List[OpenGacha]:
    """
    Get list of currently open gacha pools (time-based filtering only).

    This function only filters by openedAt/closedAt time. It does NOT check:
    - Release conditions (questClear, questNotClear)
    - Privilege conditions (privilegeValid for Start Dash)
    - Event conditions (eventScriptPlay)
    - Free draw availability

    Application layer should perform these additional checks.

    Args:
        gacha_data: Combined gacha data from fetch_combined_gacha_data()
        current_time: Current timestamp (optional, defaults to now)

    Returns:
        List of OpenGacha objects for pools that are currently open
    """
    if current_time is None:
        current_time = get_timestamp()

    # Group gacha data by gachaId
    gacha_by_id: Dict[int, List[dict]] = {}
    for gacha in gacha_data:
        gacha_id = gacha.get("gachaId", 0)
        if gacha_id not in gacha_by_id:
            gacha_by_id[gacha_id] = []
        gacha_by_id[gacha_id].append(gacha)

    open_gachas: List[OpenGacha] = []

    for gacha_id, gacha_subs in gacha_by_id.items():
        # Filter by time and sort by priority
        active_subs = [
            sub
            for sub in gacha_subs
            if sub.get("openedAt", 0) < current_time < sub.get("closedAt", 0)
        ]

        if not active_subs:
            continue

        # Sort by priority (descending) and take the highest priority one
        sorted_subs = sorted(
            active_subs, key=lambda x: x.get("priority", 0), reverse=True
        )
        selected_sub = sorted_subs[0]

        gacha_type = GachaType.from_int(selected_sub.get("type", 0))
        free_draw_flag = selected_sub.get("freeDrawFlag", 0) == 1

        open_gachas.append(
            OpenGacha(
                gacha_id=gacha_id,
                gacha_sub_id=selected_sub.get("id", 0),
                name=selected_sub.get("name", ""),
                type=gacha_type,
                image_id=selected_sub.get("imageId", 0),
                open_at=selected_sub.get("openedAt", 0),
                close_at=selected_sub.get("closedAt", 0),
                priority=selected_sub.get("priority", 0),
                common_release_id=selected_sub.get("commonReleaseId", 0),
                cond_quest_id=selected_sub.get("condQuestId", 0),
                cond_quest_phase=selected_sub.get("condQuestPhase", 0),
                free_draw_flag=free_draw_flag,
                detail_url=selected_sub.get("detailUrl", ""),
            )
        )

    return open_gachas


@lru_cache(maxsize=32)
def fetch_gacha_story_adjusts(
    gacha_id: int,
    wiki_api_url: str = "https://api.atlasacademy.io",
    timeout: int = DEFAULT_API_TIMEOUT,
) -> List[dict]:
    """
    Fetch storyAdjusts for a specific gacha from Atlas Academy API.

    Args:
        gacha_id: The gacha ID (e.g., 21001 for Story Summon)
        wiki_api_url: Base URL for the wiki API
        timeout: Request timeout in seconds (default: 15)

    Returns:
        List of storyAdjust dicts, or empty list if not found
    """
    url = f"{wiki_api_url}/nice/JP/gacha/{gacha_id}"
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("storyAdjusts", [])
    except requests.exceptions.Timeout:
        return []
    except Exception:
        return []
