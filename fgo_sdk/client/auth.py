import base64
import hashlib

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from fgo_sdk.models.config import AccountConfig, SettingsConfig


class AuthHandler:
    def __init__(self, account: AccountConfig, settings: SettingsConfig):
        self._account = account
        self.settings = settings

    def get_auth_code(self, par: dict) -> str:
        """Calculate authentication code from request parameters."""
        sorted_keys = sorted(par.keys())

        temp = ""
        for key in sorted_keys:
            value = par[key]
            if temp:
                temp += "&"

            if value is None:
                temp += f"{key}="
            elif not value and isinstance(value, str):
                temp += f"{key}="
            else:
                temp += f"{key}={value}"

        text = f"{temp}:{self._account.secret_key}"
        dig = hashlib.sha1(text.encode("utf-8")).digest()
        return base64.b64encode(dig).decode('utf-8')

    def _load_rsa_key(self):
        with open(self.settings.rsa_private_key_path, "rb") as key_file:
            content = key_file.read()
        return serialization.load_pem_private_key(content, password=None, backend=default_backend())

    def sign_data(self, uuid_str: str) -> str:
        """Sign data using RSA private key."""
        private_key = self._load_rsa_key()
        signature = private_key.sign(bytes(uuid_str, 'utf-8'), padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode('utf-8')
