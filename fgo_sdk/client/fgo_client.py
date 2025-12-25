import uuid
from urllib.parse import urlencode

import requests

from fgo_sdk.client.auth import AuthHandler
from fgo_sdk.models.config import AccountConfig, DeviceConfig, SettingsConfig
from fgo_sdk.models.game_data import GameData
from fgo_sdk.models.request_data import BasicFormData
from fgo_sdk.utils.time_tool import get_timestamp

# Disable warnings
requests.packages.urllib3.disable_warnings()


class FgoClient:
    """Low-level HTTP client for FGO API communication."""

    def __init__(
        self,
        account: AccountConfig,
        device: DeviceConfig,
        settings: SettingsConfig,
        game_data: GameData,
    ):
        self._account = account
        self._device = device
        self.settings = settings
        self.game_data = game_data
        self._auth_handler = AuthHandler(account, settings)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "*/*",
                "Accept-Encoding": "deflate, gzip",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self._device.user_agent,
                "X-Unity-Version": settings.game.x_unity_version,
            }
        )

        self._request_data = BasicFormData(
            userId=account.id,
            authKey=account.auth_key,
            appVer=game_data.app_version,
            dateVer=game_data.date_ver,
            verCode=game_data.ver_code,
            dataVer=game_data.data_ver,
        )

    def _check_response(self, operate: str, response: dict):
        data = response["response"][0]
        if data["resCode"] != "00":
            detail = data["fail"]["detail"]
            raise Exception(f"{operate} failed: {detail}")

    def _get_basic_form_data(self, with_auth=False):
        form_data = self._request_data.model_copy()
        form_data.lastAccessTime = get_timestamp()
        form_data.idempotencyKey = str(uuid.uuid4())
        if with_auth:
            form_data.authCode = self._auth_handler.get_auth_code(form_data.model_dump(exclude_none=True))
        return form_data

    def get_login_data(self):
        """Prepare login request data with signatures."""
        form_data = self._get_basic_form_data(with_auth=False)

        user_state = (-int(form_data.lastAccessTime) >> 2) ^ (
            int(form_data.userId) & self.game_data.asset_bundle_folder_crc
        )

        sign_input = f"{form_data.userId}{form_data.idempotencyKey}"
        signature = self._auth_handler.sign_data(sign_input)

        form_data.userState = str(user_state)
        form_data.assetbundleFolder = self.game_data.asset_bundle_folder
        form_data.isTerminalLogin = "1"
        form_data.idempotencyKeySignature = signature
        form_data.deviceInfo = self._device.device_info
        form_data.appCheckErrorMessage = self._device.app_check_error_message

        form_data.authCode = self._auth_handler.get_auth_code(form_data.model_dump(exclude_none=True))

        return form_data

    def create_form_data(self, extra_fields: dict = None) -> dict:
        """
        Build request data with automatic authCode calculation.
        """
        form_data = self._get_basic_form_data(with_auth=False)
        data = form_data.model_dump(exclude_none=True)

        if extra_fields:
            data.update(extra_fields)

        data['authCode'] = self._auth_handler.get_auth_code(data)
        return data

    def post(self, endpoint: str, data: dict, operate_name: str) -> dict:
        """Send POST request to FGO API."""
        url = f"{self.settings.game.host}{endpoint}?_userId={self._account.id}"

        if 'authCode' not in data or data.get('authCode') is None:
            data['authCode'] = self._auth_handler.get_auth_code(data)

        request_body = urlencode(data)

        response = self.session.post(url, data=request_body, verify=False)
        response_json = response.json()
        self._check_response(operate_name, response_json)
        return response_json
