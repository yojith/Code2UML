class Product:
    def __init__(self, sku: str):
        self.sku = sku


class Cart:
    def __init__(self):
        self.items: list[Product] = []

    def add(self, product: Product) -> None:
        self.items.append(product)
