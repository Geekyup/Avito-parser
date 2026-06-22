from bs4 import BeautifulSoup

from avito_parser.models import Item


def parse_page(html: str) -> list[Item]:
    """Парсит HTML-страницу и извлекает объявления."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all(attrs={"data-marker": "item"})

    items = []
    for card in cards:
        # Название
        title_el = card.find(attrs={"itemprop": "name"})
        title = title_el.get_text(strip=True) if title_el else ""

        # Цена
        price_meta = card.find("meta", attrs={"itemprop": "price"})
        price_raw = price_meta.get("content", "") if price_meta else ""
        price = int(price_raw) if price_raw.isdigit() else price_raw

        # Ссылка
        link_el = card.find("a", attrs={"data-marker": "item-title"})
        href = link_el.get("href", "") if link_el else ""
        url = "https://www.avito.ru" + href.split("?")[0] if href else ""

        # Локация
        loc_el = card.find(attrs={"data-marker": "item-location"})
        location = loc_el.get_text(strip=True) if loc_el else ""

        # Имя продавца
        seller_name = ""
        seller_root = card.find("div", class_="style-root-nFIJp")
        if seller_root:
            name_p = seller_root.find("p")
            if name_p:
                seller_name = name_p.get_text(strip=True)

        # Тип продавца и рейтинг
        # seller-rating присутствует только у магазинов/профи-продавцов
        rating_el = card.find(attrs={"data-marker": "seller-rating/score"})
        seller_type = "магазин" if rating_el else "частное лицо"
        seller_rating = rating_el.get_text(strip=True) if rating_el else ""

        # Отзывы
        reviews_el = card.find(attrs={"data-marker": "seller-info/summary"})
        seller_reviews_count = reviews_el.get_text(strip=True) if reviews_el else ""

        # Бейджи    
        badge_els = card.find_all(
            attrs={"data-marker": lambda v: v and v.startswith("badge-title-")}
        )
        seller_badges = "; ".join(
            b.get_text(strip=True) for b in badge_els if b.get_text(strip=True)
        )

        # Кол-во объявлений и дата регистрации
        # Только у частников; хранятся в span.iva-item-text-PvwMY (их ровно 2)
        seller_listings_count = ""
        seller_member_since = ""
        if seller_type == "частное лицо":
            spans = card.find_all("span", class_="iva-item-text-PvwMY")
            for span in spans:
                text = span.get_text(strip=True)
                if not seller_listings_count:
                    seller_listings_count = text
                else:
                    seller_member_since = text
                    break

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
    """Получает URL следующей страницы для пагинации."""
    btn = soup.find(attrs={"data-marker": "pagination-button/nextPage"})
    if btn and btn.get("href"):
        href = btn["href"]
        return "https://www.avito.ru" + href if href.startswith("/") else href
    return None