import os
import time
import threading
from typing import Optional, Dict

import requests
from pathlib import Path
from dotenv import load_dotenv

# --- Ensure .env is loaded even when this module is imported first ---
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

EKA_BASE_URL = os.environ.get("EKA_BASE_URL", "https://api.eka.care")


class TokenManager:
    """
    Manages Eka Connect access/refresh tokens using client credentials.
    - Login:   POST /connect-auth/v1/account/login
    - Refresh: POST /connect-auth/v1/account/refresh-token (V2)
    'EKA_USER_TOKEN' is OPTIONAL; will be sent only if present.
    """

    def __init__(self):
        self.api_key = os.environ.get("EKA_API_KEY")
        self.client_id = os.environ.get("EKA_CLIENT_ID")
        self.client_secret = os.environ.get("EKA_CLIENT_SECRET")
        self.user_token = os.environ.get("EKA_USER_TOKEN")  # optional

        # Fail fast if required creds are missing (after .env load above)
        for k, v in [
            ("EKA_API_KEY", self.api_key),
            ("EKA_CLIENT_ID", self.client_id),
            ("EKA_CLIENT_SECRET", self.client_secret),
        ]:
            if not v:
                raise RuntimeError(f"Missing required env: {k}. "
                                   f"Make sure backend/.env contains {k} and that it's not quoted.")

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._access_expiry: float = 0.0
        self._refresh_expiry: float = 0.0
        self._lock = threading.Lock()

    def _login(self) -> None:
        url = f"{EKA_BASE_URL}/connect-auth/v1/account/login"
        payload = {
            "api_key": self.api_key,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.user_token:
            payload["user_token"] = self.user_token  # only if provided

        r = requests.post(url, json=payload, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"Eka login failed: {r.status_code} {r.text[:300]}")

        data = r.json()
        now = time.time()
        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")
        self._access_expiry = now + float(data.get("expires_in") or 600)
        self._refresh_expiry = now + float(data.get("refresh_expires_in") or 86400)

    def _refresh(self) -> None:
        if not self._refresh_token or not self._access_token:
            self._login()
            return

        url = f"{EKA_BASE_URL}/connect-auth/v1/account/refresh-token"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        payload = {"access_token": self._access_token, "refresh_token": self._refresh_token}

        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code != 200:
            # Fallback: full login
            self._login()
            return

        data = r.json()
        now = time.time()
        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")
        self._access_expiry = now + float(data.get("expires_in") or 600)
        self._refresh_expiry = now + float(data.get("refresh_expires_in") or 86400)

    def get_access_token(self) -> str:
        with self._lock:
            now = time.time()
            if not self._access_token or (self._access_expiry - now) < 60:
                if not self._refresh_token or (self._refresh_expiry - now) < 60:
                    self._login()
                else:
                    self._refresh()
            return self._access_token  # type: ignore


# Singleton instance (safe now that .env is loaded above)
token_manager = TokenManager()


def eka_auth_header() -> Dict[str, str]:
    token = token_manager.get_access_token()
    return {"Authorization": f"Bearer {token}"}
