import os
import http.cookiejar
from typing import Optional

import requests


def load_cookies(session: requests.Session, cookies_file: Optional[str]) -> int:
    """Загружает куки из файла Netscape-формата в сессию requests.
    
    Возвращает количество загруженных куки (0, если файл не указан/не найден).
    """
    if not cookies_file or not os.path.exists(cookies_file):
        return 0

    jar = http.cookiejar.MozillaCookieJar(cookies_file)
    jar.load(ignore_discard=True, ignore_expires=True)
    session.cookies.update(jar)
    return len(jar)
