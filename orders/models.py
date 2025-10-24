from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User

class Customer(models.Model):
    customer_code = models.CharField(max_length=255,null=True, blank=True)
    name = models.CharField(max_length=255)
    credit_limit = models.PositiveIntegerField(default=120)
    credit_limit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=50000.00)
    additional_terms = models.CharField(max_length=255,blank=True, null=True)
    frequency_last_3_months = models.IntegerField(default=0)  # New field for frequency in last 3 months
    opening_balance = models.CharField(max_length=255,default='0')  # New field for opening balance


    use_next_month_start = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Role(models.Model):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Warehouse', 'Warehouse'),
        ('Security', 'Security'),
        ('Salesman', 'Salesman'),
        ('Driver','Driver'),
        ('Junaid Admin','Junaid Admin'),
        ('Accounts','Accounts'),
        ('Manager','Manager'),
        ('Collection','Collection')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Vehicle(models.Model):
    vehicle_number = models.CharField(max_length=100, unique=True)


    def __str__(self):
        return self.vehicle_number

class DeliveryOrder(models.Model):
    DRIVER_CHOICES = [
        ('Usman', 'Usman'),
        ('Acharuddin', 'Acharuddin'),
        ('Fakheer', 'Fakheer'),
        ('Nizar', 'Nizar'),
        ('Sayyam', 'Sayyam'),
        ('Customer', 'Customer'),
        ('Mukarram','Mukarram'),
        ('Shaban','Shaban'),
        ('Ameen','Ameen'),
        ('Zubair', 'Zubair')
    ]
    DO_STATUS_CHOICES = [
        ('Loaded', 'Loaded'),
        ('Delivered', 'Delivered'),
        ('Partial Delivery', 'Partial Delivery'),
        ('Out for Delivery','Out for Delivery'),
        ('Pending', 'Pending'),
        ('Not Delivered', 'Not Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Received by A/c', 'Received by A/c'),
        ('GRV','GRV'),
        ('On Hold', 'On Hold')
    ]

    do_number = models.CharField(max_length=100, unique=True)
    invoice_number=models.CharField(max_length=100,null=True,blank=True,unique=True) #newly added
    # New field for linking with Customer table
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True,related_name='delivery_orders')
    date = models.DateField()
    customer_code=models.CharField(max_length=255)
    customer_name = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    salesman=models.CharField(max_length=255,blank=True, null=True)
    salesman_mobile=models.CharField(max_length=255,blank=True, null=True)
    city=models.CharField(max_length=255,blank=True, null=True)
    area=models.CharField(max_length=255,blank=True, null=True)
    driver = models.CharField(max_length=20, choices=DRIVER_CHOICES, blank=True, null=True)
    lpo = models.CharField(max_length=255,blank=True, null=True)

    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True,related_name= 'orders')
    status = models.CharField(max_length=20, choices=DO_STATUS_CHOICES, default='Pending')

    delivery_date = models.DateTimeField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    credit_note = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        if not self.customer and self.customer_code:
            from .models import Customer  # avoid circular import
            customer_obj, created = Customer.objects.get_or_create(
                customer_code=self.customer_code,
                defaults={
                    'name': self.customer_name or self.customer_code,  # fallback to code if name is missing
                    'credit_limit': 120
                }
            )
            self.customer = customer_obj
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.do_number} - {self.city}"


class DeliveryItemWise(models.Model):
    do_number = models.CharField(max_length=100)
    item_code = models.CharField(max_length=100)
    item_description = models.CharField(max_length=255)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # other_field = models.IntegerField()  # Replace with actual field name

    def __str__(self):
        return f"{self.do_number} - {self.item_description}"





class CustomerReply(models.Model):
    sender = models.CharField(max_length=50)
    message_id = models.CharField(max_length=200)
    text_body = models.TextField()
    received_at = models.DateTimeField(auto_now_add=True)

class MessageStatus(models.Model):
    message_id = models.CharField(max_length=100, unique=True)
    recipient_id = models.CharField(max_length=20)
    status = models.CharField(max_length=20)  # sent, delivered, read, etc.
    timestamp = models.CharField(max_length=50)

    def __str__(self):
        return f"Message {self.message_id} to {self.recipient_id} - {self.status}"


class TransferOrder(models.Model):
    DRIVER_CHOICES = [
        ('Usman', 'Usman'),
        ('Acharuddin', 'Acharuddin'),
        ('Fakheer', 'Fakheer'),
        ('Nizar', 'Nizar'),
        ('Sayyam', 'Sayyam'),

    ]
    TRANSFER_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Delivered', 'Delivered'),
    ]
    t_number=models.CharField(max_length=100, unique=True)
    date = models.DateField()
    city=models.CharField(max_length=255,blank=True, null=True)
    driver = models.CharField(max_length=20, choices=DRIVER_CHOICES, blank=True, null=True)

    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True,related_name= 'transfers')
    status = models.CharField(max_length=20, choices=TRANSFER_STATUS_CHOICES, default='Pending')


class CreditBulkRequest(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    remark = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Declined', 'Declined'),
    ], default='Pending')

    def __str__(self):
        return f"BulkRequest {self.id} - {self.customer.name}"


class CreditPayment(models.Model):
    delivery_order = models.OneToOneField(
        DeliveryOrder,
        on_delete=models.CASCADE,
        to_field='invoice_number',
        db_column='invoice_number',
        related_name='credit_payment'
    )
    due_date = models.DateField()
    exceeded_days = models.IntegerField(default=0)

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Declined', 'Declined'),
    ]
    status_of_approval = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    remark = models.TextField(blank=True, null=True)
    customer_cheque_date = models.DateField(null=True, blank=True)
    bulk_request = models.ForeignKey(CreditBulkRequest, on_delete=models.SET_NULL, null=True, blank=True)
    payment_received = models.BooleanField(default=False)
    def save(self, *args, **kwargs):
        # Calculate exceeded days if the due_date is in the past
        if self.due_date and not self.payment_received:
            today = timezone.now().date()
            self.exceeded_days = (today - self.due_date).days
        super().save(*args, **kwargs)

    def __str__(self):
        return f"CreditPayment for Invoice {self.delivery_order.invoice_number} - {self.delivery_order.do_number}"



# models.py
class PreEnteredDO(models.Model):
    do_number = models.CharField(max_length=100, unique=True)
    entered_at = models.DateTimeField(auto_now_add=True)
    delivered = models.BooleanField(default=False)

    def __str__(self):
        return self.do_number


class CachedCustomerStats(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    count_every_month = models.IntegerField(default=0)
    customer_ids = models.JSONField(default=list)  # or TextField for comma-separated IDs



# --- NEW: models for SAP invoice ingestion ---
from decimal import Decimal
from django.db import models

class SAPInvoiceUploadBatch(models.Model):
    """Tracks each Excel upload for auditability and easy rollback."""
    uploaded_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    rows_ingested = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f"{self.filename} ({self.rows_ingested} rows @ {self.uploaded_at:%Y-%m-%d %H:%M})"


class SAPInvoice(models.Model):
    """
    Minimal fields required:
    - invoice_number (# second column)
    - date
    - customer_name
    - salesman
    - cancelled (Y/N -> store boolean; import only Cancelled == 'No')
    - document_total
    """
    invoice_number = models.CharField(max_length=40, unique=True, db_index=True)
    date = models.DateField(db_index=True)
    customer_name = models.CharField(max_length=255, db_index=True)
    salesman = models.CharField(max_length=128, blank=True, default="", db_index=True)
    cancelled = models.BooleanField(default=False)
    document_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    # audit
    upload_batch = models.ForeignKey(SAPInvoiceUploadBatch, on_delete=models.PROTECT, related_name="invoices")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["customer_name"]),
            models.Index(fields=["salesman"]),
        ]

    def __str__(self):
        return f"{self.invoice_number} — {self.customer_name} — {self.date}"



class SAPCreditNoteUploadBatch(models.Model):
    created_at   = models.DateTimeField(auto_now_add=True)
    filename     = models.CharField(max_length=255, blank=True, default="")
    note         = models.TextField(blank=True, default="")
    rows_ingested = models.IntegerField(default=0)

    def __str__(self):
        return f"CreditBatch {self.id} · {self.filename}"

class SAPCreditNote(models.Model):
    number         = models.CharField(max_length=64, unique=True)  # the second '#'
    date           = models.DateField(db_index=True)
    customer_name  = models.CharField(max_length=255, db_index=True)
    document_total = models.DecimalField(max_digits=18, decimal_places=2)
    upload_batch   = models.ForeignKey(SAPCreditNoteUploadBatch, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["date", "customer_name"]),
        ]

    def __str__(self):
        return f"{self.number} · {self.customer_name} · {self.date}"