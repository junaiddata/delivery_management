from orders.models import DeliveryOrder, Customer

# Step 1: Get all delivery orders with no customer FK set
orders_without_customer = DeliveryOrder.objects.filter(customer__isnull=True)

for order in orders_without_customer:
    if order.customer_name:
        customer, created = Customer.objects.get_or_create(
            name=order.customer_name,
            defaults={'credit_limit': 120}
        )
        order.customer = customer
        order.save()
        print(f"{'Created' if created else 'Linked'} customer for DO {order.do_number}")
    else:
        print(f"Skipped DO {order.do_number} (no customer_name)")
