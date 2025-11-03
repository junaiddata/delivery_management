from django.contrib import admin
from .models import *
admin.site.register(Vehicle)
@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = (
        'do_number', 'invoice_number', 'customer_name', 'customer_code', 'date',
        'status', 'driver', 'vehicle', 'amount', 'delivery_date', 'received_date'
    )
    list_filter = (
        'status', 'driver', 'date', 'city', 'area', 'salesman', 'vehicle'
    )
    search_fields = (
        'do_number', 'invoice_number', 'customer_name', 'customer_code',
        'mobile_number', 'salesman', 'salesman_mobile', 'lpo'
    )
    date_hierarchy = 'date'
    ordering = ['-date']

admin.site.register(Role)
admin.site.register(DeliveryItemWise)
admin.site.register(CustomerReply)
admin.site.register(MessageStatus)
admin.site.register(TransferOrder)
admin.site.register(CreditPayment)
admin.site.register(Customer)
admin.site.register(PreEnteredDO)
admin.site.register(SAPInvoice)
admin.site.register(SAPCreditNote)

