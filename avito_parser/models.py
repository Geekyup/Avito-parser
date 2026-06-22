from dataclasses import dataclass


@dataclass
class Item:
    title: str
    price: int | str
    location: str
    url: str
    seller_type: str
    seller_name: str
    seller_rating: str
    seller_reviews_count: str
    seller_badges: str
    seller_listings_count: str
    seller_member_since: str
