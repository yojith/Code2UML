"""
Billing models for example 5.
"""

from order import Order


class Payment:
    def __init__(self, amount: float, method: str):
        self.amount = amount
        self.method = method


class Invoice:
    def __init__(self, invoice_number: str, order: Order):
        self.invoice_number = invoice_number
        self.order: Order = order
        self.payment: Payment = Payment(0.0, "unpaid")

    def mark_paid(self, amount: float, method: str) -> None:
        self.payment = Payment(amount, method)

