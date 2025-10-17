
# from datetime import timedelta
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import DeliveryOrder, CreditPayment
# from datetime import timedelta, date

# @receiver(post_save, sender=DeliveryOrder)
# def create_credit_payment_if_ready(sender, instance, created, **kwargs):
#     if instance.status in ['Delivered', 'Received by A/c'] and instance.invoice_number:
#         if instance.invoice_number.startswith('C'):
#             return

#         if not CreditPayment.objects.filter(delivery_order=instance).exists():
#             credit_days = instance.customer.credit_limit or 120

#             # ✅ Custom logic for customers flagged to start from next month
#             if instance.customer.use_next_month_start:
#                 base_date = instance.date.replace(day=1)  # First of the current month
#                 if instance.date.month == 12:
#                     base_date = base_date.replace(year=instance.date.year + 1, month=1)
#                 else:
#                     base_date = base_date.replace(month=instance.date.month + 1)
#             else:
#                 base_date = instance.date

#             due_date = base_date + timedelta(days=credit_days)

#             CreditPayment.objects.create(
#                 delivery_order=instance,
#                 due_date=due_date
#             )

# @receiver(post_save, sender=DeliveryOrder)
# def create_credit_payment_if_ready(sender, instance, created, **kwargs):
#     if instance.status in ['Delivered', 'Received by A/c'] and instance.invoice_number:

#         if instance.invoice_number.startswith('C'):
#             return
#         # Create only if it doesn't already exist
#         if not CreditPayment.objects.filter(delivery_order=instance).exists():
#             CreditPayment.objects.create(
#                 delivery_order=instance,
#                 due_date=instance.date + timedelta(days=instance.customer.credit_limit or 120)
#             )
