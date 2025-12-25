"""Battle encryption/decryption utilities (CatGame5/MouseGame5)."""

import base64
import gzip
import struct
import zlib

from py3rijndael import RijndaelCbc, Pkcs7Padding

# AES-256 Key and IV for battle encryption (32 bytes each)
BATTLE_KEY = bytes([
    0x6F, 0x7E, 0x60, 0x49, 0x70, 0x74, 0x69, 0x7E, 0x75, 0x47, 0x4C, 0x45,
    0x62, 0x7C, 0x34, 0x34, 0x77, 0x65, 0x51, 0x35, 0x63, 0x4D, 0x6C, 0x50,
    0x6E, 0x5D, 0x47, 0x71, 0x4B, 0x40, 0x35, 0x4E
])

BATTLE_IV = bytes([
    0x7B, 0x7C, 0x79, 0x7C, 0x61, 0x7B, 0x50, 0x7B, 0x4F, 0x51, 0x79, 0x5A,
    0x5E, 0x6B, 0x79, 0x7A, 0x40, 0x5A, 0x71, 0x6C, 0x62, 0x3B, 0x63, 0x3E,
    0x7E, 0x42, 0x4B, 0x71, 0x5B, 0x7D, 0x3B, 0x6F
])

BLOCK_SIZE = 32


def cat_game5(data: bytes) -> str:
    """
    Encrypt battle result data.

    Process: raw bytes → AES-256-CBC encrypt (PKCS7 padding) → Base64 encode

    Args:
        data: Raw bytes to encrypt (typically gzip-compressed msgpack)

    Returns:
        Base64-encoded encrypted string
    """
    cipher = RijndaelCbc(
        key=BATTLE_KEY,
        iv=BATTLE_IV,
        padding=Pkcs7Padding(BLOCK_SIZE),
        block_size=BLOCK_SIZE
    )
    encrypted = cipher.encrypt(data)
    return base64.b64encode(encrypted).decode("ascii")


def mouse_game5(encrypted_b64: str) -> bytes:
    """
    Decrypt battle response data.

    Process: Base64 decode → AES-256-CBC decrypt → remove PKCS7 padding → gzip decompress

    Args:
        encrypted_b64: Base64-encoded encrypted string

    Returns:
        Decrypted and decompressed bytes
    """
    data = base64.b64decode(encrypted_b64)
    cipher = RijndaelCbc(
        key=BATTLE_KEY,
        iv=BATTLE_IV,
        padding=Pkcs7Padding(BLOCK_SIZE),
        block_size=BLOCK_SIZE
    )
    decrypted = cipher.decrypt(data)

    # Remove PKCS7 padding manually if needed
    if isinstance(decrypted, bytes) and len(decrypted) > 0:
        padding_len = decrypted[-1]
        if 0 < padding_len <= BLOCK_SIZE:
            decrypted = decrypted[:-padding_len]

    # Decompress gzip
    return gzip.decompress(decrypted)


def calc_battle_status(user_id: int, battle_id: int) -> int:
    """
    Calculate battle status CRC32 for battle result submission.

    Args:
        user_id: Player's user ID
        battle_id: Battle ID from battle setup

    Returns:
        CRC32 checksum as unsigned 32-bit integer
    """
    num = 0
    battle_status = [
        user_id + 1,
        num - 0x408FD5,
        num // 2,
        battle_id - 0x7FFFFFFF,
        num - 0x25ACF6,
    ]
    # Pack as 5 x int64 (little-endian, 40 bytes total)
    data = struct.pack('<5q', *battle_status)
    return zlib.crc32(data) & 0xFFFFFFFF
