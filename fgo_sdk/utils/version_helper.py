"""
Version helper utilities for fetching game version information.

This module provides functions to fetch the latest game version data
from external sources (Atlas Academy API and GitHub).
"""

import zlib
from dataclasses import dataclass

import requests

# Default API URLs - can be overridden by users
GAME_DATA_URL = "https://api.atlasacademy.io/raw/JP/info"
APP_VER_CODE_URL = "https://raw.githubusercontent.com/O-Isaac/FGO-VerCode-extractor/refs/heads/next/jp.json"


@dataclass
class VersionInfo:
    """Version information required for game client initialization."""

    app_version: str
    ver_code: str
    data_ver: int
    date_ver: int
    asset_bundle_folder: str
    asset_bundle_folder_crc: int


def fetch_version_info(
    game_data_url: str = GAME_DATA_URL,
    app_ver_code_url: str = APP_VER_CODE_URL,
    timeout: int = 30,
) -> VersionInfo:
    """
    Fetch version information from external sources.

    This function retrieves game version data from:
    - Atlas Academy API: dataVer, dateVer, asset bundle folder
    - GitHub (FGO-VerCode-extractor): appVer, verCode

    Args:
        game_data_url: URL for game data endpoint (dataVer, dateVer, assetbundle).
                       Default: https://api.atlasacademy.io/raw/JP/info
        app_ver_code_url: URL for app version and verCode JSON file.
                          Default: GitHub FGO-VerCode-extractor jp.json
        timeout: Request timeout in seconds. Default: 30

    Returns:
        VersionInfo dataclass containing all required version data.

    Raises:
        requests.RequestException: If any HTTP request fails.
        KeyError: If expected fields are missing from API responses.

    Example:
        >>> from fgo_sdk.utils import fetch_version_info
        >>> version = fetch_version_info()
        >>> print(f"App Version: {version.app_version}")
        >>> print(f"Data Ver: {version.data_ver}")

        # With custom URLs (e.g., for NA region)
        >>> version = fetch_version_info(
        ...     game_data_url="https://api.atlasacademy.io/raw/NA/info",
        ...     app_ver_code_url="https://example.com/na.json"
        ... )
    """
    # Fetch game data (dataVer, dateVer, assetbundle)
    game_data_resp = requests.get(game_data_url, timeout=timeout)
    game_data_resp.raise_for_status()
    game_data = game_data_resp.json()

    # Fetch app version and verCode
    ver_resp = requests.get(app_ver_code_url, timeout=timeout)
    ver_resp.raise_for_status()
    ver_info = ver_resp.json()

    # Extract asset bundle folder and calculate CRC32
    folder_name = game_data["assetbundle"]["folderName"]
    crc = zlib.crc32(folder_name.encode("utf-8")) & 0xFFFFFFFF

    return VersionInfo(
        app_version=ver_info["appVer"],
        ver_code=ver_info["verCode"],
        data_ver=game_data["dataVer"],
        date_ver=game_data["dateVer"],
        asset_bundle_folder=folder_name,
        asset_bundle_folder_crc=crc,
    )


def fetch_game_data(
    game_data_url: str = GAME_DATA_URL,
    timeout: int = 30,
) -> dict:
    """
    Fetch raw game data from external API.

    This is a lower-level function that returns the raw API response
    for users who need access to additional fields.

    Args:
        game_data_url: URL for game data endpoint.
        timeout: Request timeout in seconds.

    Returns:
        Raw dictionary containing:
        - dataVer: Data version number
        - dateVer: Date version timestamp
        - assetbundle: Asset bundle information
        - And other fields from the API

    Example:
        >>> info = fetch_game_data()
        >>> print(info["dataVer"])
        >>> print(info["assetbundle"]["folderName"])
    """
    resp = requests.get(game_data_url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_app_ver_code(
    app_ver_code_url: str = APP_VER_CODE_URL,
    timeout: int = 30,
) -> dict:
    """
    Fetch app version and verCode from external source.

    Args:
        app_ver_code_url: URL for app version/verCode JSON file.
        timeout: Request timeout in seconds.

    Returns:
        Dictionary containing:
        - appVer: Application version string
        - verCode: Version code hash

    Example:
        >>> info = fetch_app_ver_code()
        >>> print(info["appVer"])  # e.g., "2.128.1"
        >>> print(info["verCode"])  # SHA256 hash
    """
    resp = requests.get(app_ver_code_url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
