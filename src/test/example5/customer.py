"""
Customer and address models for example 5.
"""

from base import Identified


class Address:
    def __init__(self, line1: str, city: str, postal_code: str):
        self.line1 = line1
        self.city = city
        self.postal_code = postal_code


class Customer(Identified):
    def __init__(self, identifier: int, name: str, email: str):
        super().__init__(identifier)
        self.name = name
        self.email = email
        self.primary_address: Address = Address("", "", "")
        self.loyalty_points = 0

    def update_email(self, email: str) -> None:
        self.email = email

