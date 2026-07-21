class Product { String sku; }

class Cart {
    private Product featured;
    Cart(Product featured) { this.featured = featured; }
    public void add(Product product) {}
}
