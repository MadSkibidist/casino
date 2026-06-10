import json
from cryptography.fernet import Fernet

# Message constants
MSG_LOGIN        = "LOGIN"
MSG_SIGNUP       = "SIGNUP"
MSG_AUTH_OK      = "AUTH_OK"
MSG_AUTH_FAIL    = "AUTH_FAIL"
MSG_ROOM_FULL    = "ROOM_FULL"
MSG_ROOM_STATE   = "ROOM_STATE"
MSG_CHAT         = "CHAT"
MSG_CHAT_HISTORY = "CHAT_HISTORY"
MSG_BJ_UPDATE    = "BJ_UPDATE"
MSG_BJ_RESULT    = "BJ_RESULT"
MSG_ROULETTE_TICK   = "ROULETTE_TICK"
MSG_ROULETTE_RESULT = "ROULETTE_RESULT"
MSG_POKER_UPDATE = "POKER_UPDATE"
MSG_POKER_RESULT = "POKER_RESULT"

# Encryption
ENCRYPTION_KEY = b'z84H9HtM7x_5Gw-FDT_1WzohDohuzjSp9Z1iRQTFDmg='
_fernet = Fernet(ENCRYPTION_KEY)

def encrypt(data: bytes) -> bytes:
    return _fernet.encrypt(data)

def decrypt(data: bytes) -> bytes:
    return _fernet.decrypt(data)

# Framing
def encode(data_dict: dict) -> bytes:
    return (json.dumps(data_dict, ensure_ascii=False) + "\n").encode("utf-8")

def decode(byte_data: bytes) -> dict:
    try:
        return json.loads(byte_data.decode("utf-8").strip())
    except Exception:
        return {}