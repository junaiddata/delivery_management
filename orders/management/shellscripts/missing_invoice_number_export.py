import pandas as pd
from orders.models import DeliveryOrder

# Fetch all DOs without an invoice number (either NULL or empty string)
orders = DeliveryOrder.objects.filter(invoice_number__isnull=True) | DeliveryOrder.objects.filter(invoice_number='')

# Create a list of dictionaries
data = []
for order in orders:
    data.append({
        'DO': order.do_number,
        'Customer Name': order.customer_name,
        'Date': order.date,
        'Amount': order.amount,
        'City': order.city,
        'Area': order.area,
        # Add more fields if you want
    })

# Convert to DataFrame
df = pd.DataFrame(data)

# Export to Excel
df.to_excel("dos_without_invoice.xlsx", index=False)
print("Exported DOs without invoice number to 'dos_without_invoice.xlsx'")
