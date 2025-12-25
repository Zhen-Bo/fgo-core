import base64
import gzip

import msgpack
import py3rijndael

# AES-256 key for asset bundle decryption
ASSET_BUNDLE_KEY = b"W0Juh4cFJSYPkebJB9WpswNF51oa6Gm7"


def get_asset_bundle(assetbundle: str) -> dict:
    """Decrypt and decompress asset bundle data."""
    data = base64.b64decode(assetbundle)
    iv = data[:32]
    array = data[32:]

    cipher = py3rijndael.RijndaelCbc(
        ASSET_BUNDLE_KEY, iv, py3rijndael.paddings.Pkcs7Padding(16), 32
    )

    data = cipher.decrypt(array)
    gzip_data = gzip.decompress(data)
    data_unpacked = msgpack.unpackb(gzip_data)

    return data_unpacked
