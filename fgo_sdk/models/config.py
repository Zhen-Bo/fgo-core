from typing import Optional

from pydantic import BaseModel


class DeviceConfig(BaseModel):
    """Device configuration for API requests.

    This is intentionally separate from AccountConfig to allow flexibility:
    - Multiple accounts can share the same device config
    - Single account can use different devices
    - Application layer decides how to organize configs
    """
    device_info: str
    user_agent: str
    app_check_error_message: Optional[str] = ""


class GameConfig(BaseModel):
    package_name: str
    host: str
    x_unity_version: str


class UrlConfig(BaseModel):
    wiki_api: str
    gacha_data: str
    vercode_info_url: str


class SettingsConfig(BaseModel):
    rsa_private_key_path: str
    game: GameConfig
    url: UrlConfig


class AccountConfig(BaseModel):
    """Account credentials for authentication.

    Note: DeviceConfig is intentionally NOT included here.
    The SDK receives account and device separately, giving the application
    layer full control over how to organize and associate them.
    """
    id: int
    auth_key: str
    secret_key: str
