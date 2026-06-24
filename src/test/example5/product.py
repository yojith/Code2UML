"""
Product models for example 5.
"""

from base import Identified, Timestamped


class Product(Identified, Timestamped):
    def __init__(self, identifier: int, name: str, price: float):
        Identified.__init__(self, identifier)
        Timestamped.__init__(self)
        self.name = name
        self.price = price

    def apply_discount(self, percentage: float) -> float:
        return self.price * (1 - percentage / 100)


class DigitalProduct(Product):
    def __init__(self, identifier: int, name: str, price: float, download_url: str):
        super().__init__(identifier, name, price)
        self.download_url = download_url

