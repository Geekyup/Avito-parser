import time
import random
import logging
import os
from typing import Callable, Optional

from curl_cffi import requests
from bs4 import BeautifulSoup

from avito_parser.models import Item
from avito_parser.parser import parse_page, get_next_url
from avito_parser.cookies import load_cookies
from avito_parser.xlsx_writer import save_to_xlsx


DELAY_MIN = 3.0
DELAY_MAX = 6.0

IMPERSONATE = "chrome124"  


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


class ScrapingCancelled(Exception):
    """Выбрасывается, когда пользователь нажал 'Остановить' в GUI."""
    pass


def run_scraping(
    start_url: str,
    max_pages: int,
    output_file: str,
    cookies_file: Optional[str] = None,
    delay_min: float = DELAY_MIN,
    delay_max: float = DELAY_MAX,
    log_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> tuple[int, str]:
    """
    Запускает сбор объявлений и сохраняет результат в xlsx.

    Args:
        start_url: Начальная ссылка на поиск Avito
        max_pages: Максимальное количество страниц для парсинга
        output_file: Путь к выходному файлу
        cookies_file: Путь к файлу cookies в Netscape формате
        delay_min: Минимальная пауза между запросами (сек)
        delay_max: Максимальная пауза между запросами (сек)
        log_callback: Функция для вывода логов (обычно для GUI)
        progress_callback: Функция для обновления прогресса
        should_cancel: Функция для проверки, нужно ли прервать

    Returns:
        Кортеж (количество_собранных_объявлений, путь_к_файлу)
        
    Raises:
        ScrapingCancelled: Если пользователь прервал сбор
    """

    def emit(msg: str) -> None:
        log.info(msg)
        if log_callback:
            log_callback(msg)

    session = requests.Session(impersonate=IMPERSONATE)

    n_cookies = load_cookies(session, cookies_file)
    if n_cookies:
        emit(f"Загружено {n_cookies} куки из {cookies_file}")
    else:
        emit("Куки не загружены — запросы пойдут без авторизации.")

    all_items: list[Item] = []
    url = start_url

    for page_num in range(1, max_pages + 1):
        if should_cancel and should_cancel():
            emit("Остановлено пользователем.")
            raise ScrapingCancelled()

        if progress_callback:
            progress_callback(page_num, max_pages)

        emit(f"Страница {page_num}/{max_pages} → {url}")

        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.errors.RequestsError as e:
            emit(f"Ошибка запроса: {e}")
            break

        emit(f"Получено {len(resp.text)} байт, статус {resp.status_code}")

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all(attrs={"data-marker": "item"})

        if not cards:
            dump_file = f"debug_page_{page_num}.html"
            with open(dump_file, "w", encoding="utf-8") as f:
                f.write(resp.text)
            emit(f"Карточки не найдены! Похоже на капчу/блокировку. Дамп → {dump_file}")
            break

        items = parse_page(resp.text)
        all_items.extend(items)
        emit(f"Карточек на странице: {len(items)}. Итого собрано: {len(all_items)}")

        next_url = get_next_url(soup)
        if not next_url or page_num >= max_pages:
            emit("Пагинация завершена.")
            break

        url = next_url

        if page_num < max_pages:
            delay = random.uniform(delay_min, delay_max)
            emit(f"Пауза {delay:.1f}с...")
            time.sleep(delay)

    if all_items:
        save_to_xlsx(all_items, output_file)
        emit(f"Сохранено {len(all_items)} записей → {os.path.abspath(output_file)}")
    else:
        emit("Нет данных для сохранения.")

    return len(all_items), os.path.abspath(output_file)