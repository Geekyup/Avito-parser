import os
import http.cookiejar
from typing import Optional

from curl_cffi import requests as curl_requests


def load_cookies(session: curl_requests.Session, cookies_file: Optional[str]) -> int:
    """Загружает куки из файла Netscape-формата в сессию curl_cffi.
    
    Возвращает количество загруженных куки (0, если файл не указан/не найден).
    """
    if not cookies_file or not os.path.exists(cookies_file):
        return 0

    jar = http.cookiejar.MozillaCookieJar(cookies_file)
    jar.load(ignore_discard=True, ignore_expires=True)

    for cookie in jar:
        session.cookies.set(cookie.name, cookie.value, domain=cookie.domain)

    return len(jar)