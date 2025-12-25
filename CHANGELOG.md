# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1-alpha] - 2025-12-25

### Added

- Initial release of FGO SDK
- Core HTTP client (`FgoClient`) with authentication and request signing
- Service layer implementation:
  - `LoginService` - Account login and session management
  - `BattleService` - Complete battle flow with automatic encryption
  - `GachaService` - Gacha/summoning operations
  - `PresentService` - Gift box management
  - `ShopService` - Mana prism shop operations
  - `ItemService` - AP recovery (apple usage)
  - `FollowerService` - Support friend list operations
- Configuration classes:
  - `AccountConfig` - Account credentials
  - `DeviceConfig` - Device information (shareable across accounts)
  - `SettingsConfig` - SDK settings
- Battle encryption/decryption utilities (CatGame5/MouseGame5)
- RSA signature support for authentication
- Atlas Academy API integration for game data lookup

### Notes

- This is an alpha release for testing purposes
- RSA private keys must be in PKCS#8 format

[0.0.1-alpha]: https://github.com/Zhen-Bo/fgo-core/releases/tag/v0.0.1-alpha
