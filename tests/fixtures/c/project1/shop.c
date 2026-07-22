#include "shop.h"

void cart_add(struct Cart *self, struct Product *product) {
    self->featured = product;
}
