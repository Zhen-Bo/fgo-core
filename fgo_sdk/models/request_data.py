from pydantic import BaseModel


class BasicFormData(BaseModel):
    userId: int
    authKey: str
    appVer: str
    dateVer: int
    verCode: str
    dataVer: int

    lastAccessTime: int | None = None
    idempotencyKey: str | None = None
    authCode: str | None = None

    # Login specific fields
    idempotencyKeySignature: str | None = None
    deviceInfo: str | None = None
    userState: str | int | None = None
    assetbundleFolder: str | None = None
    appCheckErrorMessage: str | None = None
    isTerminalLogin: str | None = None
