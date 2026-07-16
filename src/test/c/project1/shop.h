#define CART_LIMIT 20

struct Product { int sku; };
struct Cart { struct Product *featured; };

void cart_add(struct Cart *self, struct Product *product);
