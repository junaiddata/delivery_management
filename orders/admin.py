from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field
from .models import *
from orders.api_client import normalize_mobile_number

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
    list_per_page = 300  # Show 300 items per page in admin

admin.site.register(Role)
admin.site.register(DeliveryItemWise)
admin.site.register(CustomerReply)
admin.site.register(MessageStatus)
admin.site.register(TransferOrder)
admin.site.register(CreditPayment)
class CustomerResource(resources.ModelResource):
    """
    Resource for importing Customer mobile numbers from Excel
    Required Excel columns:
    - customer_code: Customer code (e.g., HO02525)
    - mobile_number: Phone number in any format (will be normalized automatically)
    """
    customer_code = Field(attribute='customer_code', column_name='customer_code')
    mobile_number = Field(attribute='mobile_number', column_name='mobile_number')
    
    class Meta:
        model = Customer
        fields = ('customer_code', 'mobile_number')
        import_id_fields = ('customer_code',)
        skip_unchanged = True
        report_skipped = False
    
    def before_import_row(self, row, **kwargs):
        """Normalize mobile number before importing"""
        if 'mobile_number' in row and row['mobile_number']:
            normalized = normalize_mobile_number(row['mobile_number'])
            if normalized:
                row['mobile_number'] = normalized
            else:
                # If normalization fails, keep original but log warning
                pass

@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin):
    list_display = ('customer_code', 'name', 'mobile_number', 'credit_limit', 'credit_limit_amount')
    list_filter = ('credit_limit',)
    search_fields = ('customer_code', 'name', 'mobile_number')
    resource_class = CustomerResource
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer_code', 'name', 'mobile_number')
        }),
        ('Credit Settings', {
            'fields': ('credit_limit', 'credit_limit_amount', 'additional_terms')
        }),
        ('Other', {
            'fields': ('frequency_last_3_months', 'opening_balance', 'use_next_month_start')
        }),
    )
admin.site.register(PreEnteredDO)
admin.site.register(SAPInvoice)
admin.site.register(SAPCreditNote)
admin.site.register(SAPCreditNoteUploadBatch)
admin.site.register(SAPInvoiceUploadBatch)


