"""
Django management command to sync invoice numbers from DOInvoice API
"""
import logging
import uuid
import requests
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from orders.api_client import SAPAPIClient
from orders.models import DeliveryOrder, CreditPayment

# Configure logging
logger = logging.getLogger(__name__)


def generate_random_invoice():
    """Generate random invoice number in format C{12-char-hex}"""
    return f"C{uuid.uuid4().hex[:12].upper()}"


def normalize_invoice(invoice_value):
    """
    Normalize invoice value from API:
    - null/None/empty/NIL -> generate random invoice
    - Otherwise -> return as string
    
    Args:
        invoice_value: Invoice value from API (can be None, null, string, number)
        
    Returns:
        String invoice number (random if null/NIL, otherwise original value as string)
    """
    if invoice_value is None:
        return generate_random_invoice()
    
    invoice_str = str(invoice_value).strip()
    
    if not invoice_str or invoice_str.upper() == 'NIL':
        return generate_random_invoice()
    
    return invoice_str


def make_invoice_unique(base_invoice, current_order):
    """
    Make invoice number unique by suffixing -A, -B, etc if needed
    
    Args:
        base_invoice: Base invoice number to use
        current_order: DeliveryOrder instance (may already have an invoice)
        
    Returns:
        Unique invoice number (may be base_invoice or base_invoice-A, -B, etc)
    """
    # Check if current order already has a matching invoice (stability rule)
    if current_order.invoice_number:
        current_inv = current_order.invoice_number
        # If current invoice matches base or is base-X format, check if it's still available
        if current_inv == base_invoice:
            # Check if this invoice is still available (not used by another order)
            if not DeliveryOrder.objects.exclude(pk=current_order.pk).filter(invoice_number=base_invoice).exists():
                return base_invoice
        elif current_inv.startswith(base_invoice + '-'):
            # Current invoice is base-X format, check if still available
            if not DeliveryOrder.objects.exclude(pk=current_order.pk).filter(invoice_number=current_inv).exists():
                return current_inv
    
    # Try base_invoice first
    if not DeliveryOrder.objects.exclude(pk=current_order.pk).filter(invoice_number=base_invoice).exists():
        return base_invoice
    
    # Try with suffix -A, -B, -C, etc
    suffix_letter = ord('A')
    while suffix_letter <= ord('Z'):
        candidate = f"{base_invoice}-{chr(suffix_letter)}"
        if not DeliveryOrder.objects.exclude(pk=current_order.pk).filter(invoice_number=candidate).exists():
            return candidate
        suffix_letter += 1
    
    # If all A-Z are taken, fall back to random (shouldn't happen in practice)
    logger.warning(f"All suffixes A-Z taken for invoice {base_invoice}, using random invoice")
    return generate_random_invoice()


class Command(BaseCommand):
    help = 'Sync invoice numbers from DOInvoice API for last 3 days'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days-back',
            type=int,
            default=3,
            help='Number of days to look back (default: 3, meaning last 3 days including today)'
        )
        parser.add_argument(
            '--from-date',
            type=str,
            help='Start date (YYYY-MM-DD format). If provided, overrides --days-back'
        )
        parser.add_argument(
            '--to-date',
            type=str,
            help='End date (YYYY-MM-DD format). Defaults to today if not provided'
        )
        parser.add_argument(
            '--save-local',
            action='store_true',
            help='Save directly to local database (bypasses HTTP push to VPS)'
        )
        parser.add_argument(
            '--local-only',
            action='store_true',
            help='Test mode: fetch from API but do not push to VPS or save to database'
        )
    
    def handle(self, *args, **options):
        start_time = datetime.now()
        
        self.stdout.write(self.style.SUCCESS('Starting invoice sync from DOInvoice API...'))
        
        # Determine date range
        today = date.today()
        
        if options['from_date'] and options['to_date']:
            try:
                from_date = datetime.strptime(options['from_date'], '%Y-%m-%d').date()
                to_date = datetime.strptime(options['to_date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
        elif options['from_date']:
            try:
                from_date = datetime.strptime(options['from_date'], '%Y-%m-%d').date()
                to_date = today
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
        elif options['to_date']:
            try:
                to_date = datetime.strptime(options['to_date'], '%Y-%m-%d').date()
                days_back = options['days_back']
                from_date = to_date - timedelta(days=days_back - 1)  # -1 because we include to_date
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
        else:
            # Default: last 3 days including today
            days_back = options['days_back']
            to_date = today
            from_date = today - timedelta(days=days_back - 1)  # -1 because we include today
        
        self.stdout.write(f"Fetching invoices from {from_date} to {to_date}")
        
        # Initialize API client
        client = SAPAPIClient()
        
        # Fetch invoice data
        invoice_records = client.fetch_do_invoices(from_date, to_date)
        
        if not invoice_records:
            self.stdout.write(self.style.WARNING('No invoice records fetched from API'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Fetched {len(invoice_records)} invoice records from API'))
        
        # Group by DO number (API returns line items, we need one record per DO)
        do_invoice_map = {}
        for record in invoice_records:
            do_number = str(record.get('DO', '')).strip()
            if not do_number:
                continue
            
            invoice_value = record.get('INVOICE')
            amount_value = record.get('AMOUNT')
            
            # Parse amount
            amount = None
            if amount_value is not None:
                try:
                    amount = Decimal(str(amount_value))
                except (InvalidOperation, ValueError, TypeError):
                    logger.warning(f"Invalid amount for DO {do_number}: {amount_value}")
            
            # Group by DO - keep the invoice and amount (they should be same for all lines of same DO)
            if do_number not in do_invoice_map:
                do_invoice_map[do_number] = {
                    'invoice': invoice_value,
                    'amount': amount
                }
            else:
                # If amount is None in first record but available in later record, update it
                if do_invoice_map[do_number]['amount'] is None and amount is not None:
                    do_invoice_map[do_number]['amount'] = amount
        
        self.stdout.write(f'Grouped to {len(do_invoice_map)} unique DOs')
        
        # Process each DO
        stats = {
            'updated': 0,
            'not_found': 0,
            'skipped': 0,
            'duplicates_resolved': 0,
            'credit_payments_deleted': 0,
            'errors': 0
        }
        
        errors = []
        updated_orders = []  # Store updated orders for VPS push
        
        # Process invoices
        if options['local_only']:
            self.stdout.write(self.style.WARNING('--local-only mode: Will not save or push'))
        elif options['save_local']:
            self.stdout.write('Mode: Save to local database only')
        else:
            self.stdout.write('Mode: Save locally and push to VPS')
        
        try:
            with transaction.atomic():
                for do_number, invoice_data in do_invoice_map.items():
                    try:
                        # Find the delivery order
                        try:
                            order = DeliveryOrder.objects.get(do_number=do_number)
                        except DeliveryOrder.DoesNotExist:
                            stats['not_found'] += 1
                            logger.debug(f"DO {do_number} not found in database")
                            continue
                        
                        # Normalize invoice (handle null/NIL)
                        base_invoice = normalize_invoice(invoice_data['invoice'])
                        
                        # Make invoice unique
                        old_invoice = order.invoice_number
                        final_invoice = make_invoice_unique(base_invoice, order)
                        
                        if final_invoice != base_invoice:
                            stats['duplicates_resolved'] += 1
                            logger.debug(f"DO {do_number}: Invoice {base_invoice} -> {final_invoice} (duplicate resolved)")
                        
                        # If invoice is changing and there was an old invoice, delete CreditPayment
                        if old_invoice and old_invoice != final_invoice:
                            deleted_count = CreditPayment.objects.filter(delivery_order=order).delete()[0]
                            if deleted_count > 0:
                                stats['credit_payments_deleted'] += deleted_count
                                logger.debug(f"DO {do_number}: Deleted {deleted_count} CreditPayment record(s) due to invoice change")
                        
                        # Update invoice number and amount
                        order.invoice_number = final_invoice
                        if invoice_data['amount'] is not None:
                            order.amount = invoice_data['amount']
                        
                        if not options['local_only']:
                            order.save()
                            stats['updated'] += 1
                            
                            # Store for VPS push (format similar to delivery orders sync)
                            updated_orders.append({
                                'do_number': order.do_number,
                                'invoice_number': final_invoice,
                                'amount': str(order.amount) if order.amount else None,
                                'date': order.date.isoformat() if order.date else None,
                                'customer_code': order.customer_code,
                                'customer_name': order.customer_name,
                            })
                        
                    except Exception as e:
                        stats['errors'] += 1
                        error_msg = f"Error processing DO {do_number}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg, exc_info=True)
            
            # Push to VPS if not in local-only or save-local mode
            if not options['local_only'] and not options['save_local']:
                self._push_to_vps(updated_orders, from_date, to_date, stats)
            
            # Summary
            mode_str = "Local only (test)" if options['local_only'] else "Save local" if options['save_local'] else "Full sync (local + VPS)"
            self.stdout.write(self.style.SUCCESS(
                f'\n========= INVOICE SYNC SUMMARY =========\n'
                f'Duration: {(datetime.now() - start_time).total_seconds():.2f} seconds\n'
                f'Date range: {from_date} to {to_date}\n'
                f'Mode: {mode_str}\n'
                f'Records fetched: {len(invoice_records)}\n'
                f'Unique DOs: {len(do_invoice_map)}\n'
                f'Updated: {stats["updated"]}\n'
                f'Not found: {stats["not_found"]}\n'
                f'Duplicates resolved: {stats["duplicates_resolved"]}\n'
                f'Credit payments deleted: {stats["credit_payments_deleted"]}\n'
                f'Errors: {stats["errors"]}\n'
                f'=========================================='
            ))
            
            if errors:
                self.stdout.write(self.style.WARNING(f"\nWarnings: {len(errors)} errors occurred"))
                for error in errors[:10]:  # Show first 10 errors
                    self.stdout.write(self.style.WARNING(f"  - {error}"))
                if len(errors) > 10:
                    self.stdout.write(self.style.WARNING(f"  ... and {len(errors) - 10} more errors"))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error during invoice sync: {e}"))
            logger.error(f"Invoice sync error: {e}", exc_info=True)
    
    def _push_to_vps(self, updated_orders, from_date, to_date, stats):
        """Push invoice updates to VPS"""
        vps_url = getattr(settings, 'VPS_RECEIVE_URL', None)
        if not vps_url:
            # Use the production VPS URL
            vps_url = "https://do.junaidworld.com/api/sync/delivery-orders/"
        
        api_key = getattr(settings, 'VPS_API_KEY', '')
        if not api_key:
            self.stdout.write(self.style.ERROR('VPS_API_KEY not configured in settings'))
            return
        
        if not updated_orders:
            self.stdout.write(self.style.WARNING('No orders to send to VPS'))
            return
        
        # Format payload similar to delivery orders sync
        # Mark as invoice_update_only to ensure VPS only updates existing records
        payload = {
            'records': updated_orders,
            'api_key': api_key,
            'sync_metadata': {
                'sync_time': datetime.now().isoformat(),
                'records_count': len(updated_orders),
                'from_date': from_date.isoformat(),
                'to_date': to_date.isoformat(),
                'sync_type': 'invoice_update',
                'update_only': True  # Flag to indicate this should only update, not create
            }
        }
        
        try:
            self.stdout.write(f'Sending {len(updated_orders)} invoice updates to VPS: {vps_url}')
            response = requests.post(
                vps_url,
                json=payload,
                timeout=60,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                vps_stats = result.get('stats', {})
                self.stdout.write(self.style.SUCCESS(
                    f"[OK] VPS sync successful! Updated: {vps_stats.get('updated', 0)}, "
                    f"Errors: {vps_stats.get('errors', 0)}"
                ))
            else:
                error_msg = result.get('error', 'Unknown error')
                self.stdout.write(self.style.ERROR(f"[ERROR] VPS sync failed: {error_msg}"))
                logger.error(f"VPS sync failed: {error_msg}")
                
        except requests.exceptions.HTTPError as e:
            error_details = f"{e}"
            try:
                if e.response is not None:
                    error_body = e.response.text
                    error_details = f"{e} - Response: {error_body}"
                    try:
                        error_json = e.response.json()
                        if 'error' in error_json:
                            error_details = f"{e} - Error: {error_json.get('error')}"
                    except:
                        pass
            except:
                pass
            self.stdout.write(self.style.ERROR(f"[ERROR] HTTP Error sending to VPS: {error_details}"))
            logger.error(f"VPS sync HTTP error: {error_details}")
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error sending to VPS: {e}"))
            logger.error(f"VPS sync error: {e}")
