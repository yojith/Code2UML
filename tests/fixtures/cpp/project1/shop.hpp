struct Product { int sku; };

class Cart {
public:
    void add(Product* product);
private:
    Product* featured;
};
