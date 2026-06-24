"""
Order workflow models for example 5.
"""

from customer import Customer
from product import Product


class OrderItem:
    def __init__(self, product: Product, quantity: int):
        self.product: Product = product
        self.quantity = quantity


class Order:
    def __init__(self, order_id: int, customer: Customer):
        self.order_id = order_id
        self.customer: Customer = customer
        self.items: list[OrderItem] = []
        self.status = "draft"

    def add_item(self, item: OrderItem) -> None:
        self.items.append(item)

    def submit(self) -> None:
        self.status = "submitted"

