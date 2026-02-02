"""
Django management command to convert all existing salesman names to uppercase
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import DeliveryOrder

class Command(BaseCommand):
    help = 'Convert all existing salesman names to uppercase'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually updating the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get all orders with non-null salesman names
        orders = DeliveryOrder.objects.exclude(salesman__isnull=True).exclude(salesman='')
        
        total_count = orders.count()
        updated_count = 0
        
        self.stdout.write(f"Found {total_count} orders with salesman names")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
        
        # Process in batches for efficiency
        batch_size = 1000
        to_update = []
        
        for order in orders:
            if order.salesman:
                original = order.salesman
                uppercase = original.upper()
                
                # Only update if it's different
                if original != uppercase:
                    if dry_run:
                        self.stdout.write(f"  Would update: '{original}' -> '{uppercase}' (DO: {order.do_number})")
                    else:
                        order.salesman = uppercase
                        to_update.append(order)
                    updated_count += 1
        
        if not dry_run and to_update:
            self.stdout.write(f"\nUpdating {len(to_update)} orders...")
            
            with transaction.atomic():
                # Use bulk_update for efficiency
                DeliveryOrder.objects.bulk_update(to_update, ['salesman'], batch_size=batch_size)
            
            self.stdout.write(self.style.SUCCESS(
                f"✅ Successfully updated {updated_count} salesman names to uppercase"
            ))
        elif dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"✅ Would update {updated_count} salesman names to uppercase"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "✅ All salesman names are already uppercase or empty"
            ))
