from bs4 import BeautifulSoup

from avito_parser.models import Item


def parse_page(html: str) -> list[Item]:
    """Парсит HTML-страницу и извлекает объявления.
    
    Args:
        html: HTML-содержимое страницы
        
    Returns:
        Список объявлений (Item)
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all(attrs={"data-marker": "item"})

    items = []
    for card in cards:
        title_el = card.find(attrs={"itemprop": "name"})
        title = title_el.get_text(strip=True) if title_el else ""

        price_el = card.find("meta", attrs={"itemprop": "price"})
        price_raw = price_el["content"] if price_el else ""
        price = int(price_raw) if price_raw.isdigit() else price_raw

        link_el = card.find("a", attrs={"data-marker": "item-title"})
        href = link_el.get("href", "") if link_el else ""
        url = "https://www.avito.ru" + href.split("?")[0] if href else ""

        loc_el = card.find(attrs={"data-marker": "item-location"})
        location = loc_el.get_text(strip=True) if loc_el else ""

        seller_el = card.select_one('[data-marker="item-user-logo"] + p, .style-root-nFIJp p')
        seller_name = seller_el.get_text(strip=True) if seller_el else ""

        rating_el = card.find(attrs={"data-marker": "seller-rating/score"})
        seller_type = "магазин" if rating_el else "частное лицо"
        seller_rating = rating_el.get_text(strip=True) if rating_el else ""

        reviews_el = card.find(attrs={"data-marker": "seller-info/summary"})
        seller_reviews_count = reviews_el.get_text(strip=True) if reviews_el else ""

        badge_els = card.find_all(attrs={"data-marker": lambda v: v and v.startswith("badge-title-")})
        seller_badges = "; ".join(b.get_text(strip=True) for b in badge_els if b.get_text(strip=True))

        seller_listings_count = ""
        seller_member_since = ""
        if seller_type == "частное лицо":
            info_texts = [s.get_text(strip=True) for s in card.select(".iva-item-text-PvwMY")]
            for text in info_texts:
                if "объявлен" in text:
                    seller_listings_count = text
                elif "Авито" in text:
                    seller_member_since = text

        if title or price:
            items.append(Item(
                title=title,
                price=price,
                location=location,
                url=url,
                seller_type=seller_type,
                seller_name=seller_name,
                seller_rating=seller_rating,
                seller_reviews_count=seller_reviews_count,
                seller_badges=seller_badges,
                seller_listings_count=seller_listings_count,
                seller_member_since=seller_member_since,
            ))

    return items


def get_next_url(soup: BeautifulSoup) -> str | None:
    """Получает URL следующей страницы для пагинации.
    
    Args:
        soup: Объект BeautifulSoup с разобранной страницей
        
    Returns:
        URL следующей страницы или None, если пагинация закончена
    """
    btn = soup.find(attrs={"data-marker": "pagination-button/nextPage"})
    if btn and btn.get("href"):
        href = btn["href"]
        return "https://www.avito.ru" + href if href.startswith("/") else href
    return None
