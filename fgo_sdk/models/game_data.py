from pydantic import BaseModel


class VersionData(BaseModel):
    serverHash: str
    assetbundle: str
    master: str
    dataVer: int
    dateVer: int
    assetbundleKey: str


class GameData(BaseModel):
    app_version: str
    ver_code: str
    data_ver: int
    date_ver: int
    asset_bundle_folder: str
    asset_bundle_folder_crc: int
