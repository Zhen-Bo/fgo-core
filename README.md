# FGO SDK

Python SDK for Fate/Grand Order API communication and data parsing.

## Design Philosophy

This SDK follows a **neutral, unopinionated design**:

- SDK handles **only** API communication, data parsing, and encryption
- **No** automatic decision-making logic (e.g., auto-select items)
- **No** business preferences or strategies built-in
- Application layer (CLI/Bot) decides how to use the data

## Installation

```bash
pip install fgo-sdk
```

Or install from source:

```bash
git clone https://github.com/Zhen-Bo/fgo-core.git
cd fgo-core
pip install -e .
```

## Features

| Service | Description |
|---------|-------------|
| **FgoClient** | Core HTTP client with authentication and request signing |
| **LoginService** | Account login and session management |
| **ShopService** | Mana prism shop operations |
| **GachaService** | Gacha/summoning operations |
| **PresentService** | Gift box management |
| **ItemService** | AP recovery (apple usage) |
| **FollowerService** | Support friend list operations |
| **BattleService** | Complete battle flow with automatic encryption |

## Quick Start

```python
from fgo_sdk import FgoClient, AccountConfig, DeviceConfig, LoginService, BattleService

# Configure account (credentials only)
account = AccountConfig(
    id=123456789,
    auth_key="your_auth_key",
    secret_key="your_secret_key",
)

# Configure device (can be shared across accounts)
device = DeviceConfig(
    device_info="...",
    user_agent="...",
)

# Initialize client with separate account and device
client = FgoClient(account, device, settings, game_data)

# Login
login_service = LoginService(client)
result = login_service.login()

# Battle operations
battle_service = BattleService(client)
setup = battle_service.battle_setup(
    quest_id=94000502,
    quest_phase=1,
    deck_id=1,
    follower_id=123456,
    follower_type=2,
    follower_class_id=7,
)
```

## External APIs

This SDK uses [Atlas Academy API](https://github.com/atlasacademy/fgo-game-data-api) for game data lookup.

## API Quick Reference

### Configuration Classes

```python
from fgo_sdk import AccountConfig, DeviceConfig, SettingsConfig

# Account credentials
AccountConfig(id, auth_key, secret_key)

# Device info (can be shared across accounts)
DeviceConfig(device_info, user_agent, app_check_error_message?)
```

### Services

| Service | Key Methods |
|---------|-------------|
| `LoginService(client)` | `.login()` → `LoginResult` |
| `BattleService(client)` | `.battle_setup(...)`, `.battle_result(...)` |
| `GachaService(client, wiki_url)` | `.draw_fp_gacha(...)` → `GachaResult` |
| `PresentService(client, wiki_url)` | `.get_presents()`, `.receive_present(...)` |
| `ShopService(client)` | `.get_shop_list()`, `.buy_item(...)` |
| `ItemService(client)` | `.use_apple(apple_id)` |
| `FollowerService(client)` | `.get_follower_list(...)` |

### Return Types

```python
# LoginResult
result.player_data      # PlayerData
result.user_quest       # List[UserQuest]

# PlayerData
player_data.player_info.name
player_data.player_info.level
player_data.ownedItem.quartz
player_data.ownedItem.friend_point

# GachaResult
gacha_result.success    # bool
gacha_result.items      # List[GachaObtainItem]
```

## Requirements

- Python 3.10+
- requests
- cryptography (>=41.0.0)
- msgpack
- py3rijndael
- pydantic

## RSA Key Format

This SDK requires RSA private keys in **PKCS#8 format**.

If you have an older key in PKCS#1 format (`-----BEGIN RSA PRIVATE KEY-----`), convert it using:

```bash
openssl rsa -in private_key.pem -outform PEM -out private_key.pem
```

After conversion, the key should start with `-----BEGIN PRIVATE KEY-----`.

## License

MIT License
