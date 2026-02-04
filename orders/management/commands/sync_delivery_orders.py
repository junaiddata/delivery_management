"""
Django management command to sync delivery orders from SAP API to cloud VPS
"""
import json
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
import requests
from orders.api_client import SAPAPIClient
from orders.models import DeliveryOrder, DeliveryItemWise

# Configure logging
logger = logging.getLogger(__name__)


def serialize_for_json(data):
    """
    Serialize data for JSON transport (convert dates, decimals to strings)
    
    Args:
        data: List of dicts with model data
        
    Returns:
        List of dicts with serialized values
    """
    serialized = []
    for record in data:
        serialized_record = {}
        for key, value in record.items():
            if key == 'document_lines':
                # Keep document_lines as-is (will be processed separately)
                serialized_record[key] = value
            elif isinstance(value, datetime):
                serialized_record[key] = value.isoformat()
            elif isinstance(value, date):  # date object
                serialized_record[key] = value.isoformat()
            elif isinstance(value, Decimal):
                serialized_record[key] = str(value)
            elif value is None:
                serialized_record[key] = None
            else:
                serialized_record[key] = value
        serialized.append(serialized_record)
    return serialized


class Command(BaseCommand):
    help = 'Sync delivery orders from SAP API to cloud VPS'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days-back',
            type=int,
            default=getattr(settings, 'SYNC_DAYS_BACK', 3),
            help='Number of days to look back (default: 3)'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Sync specific date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--id',
            type=int,
            help='Sync single record by DocNum'
        )
        parser.add_argument(
            '--local-only',
            action='store_true',
            help='Test mode: fetch from API but do not push to VPS or save to database'
        )
        parser.add_argument(
            '--save-local',
            action='store_true',
            help='Save directly to local database (bypasses HTTP push to VPS)'
        )
    
    def handle(self, *args, **options):
        start_time = datetime.now()
        
        self.stdout.write(self.style.SUCCESS('Starting delivery order sync...'))
        
        # Initialize API client
        client = SAPAPIClient()
        
        # Step 1: FETCH from internal API
        records = []
        
        if options['id']:
            # Fetch single record by DocNum
            self.stdout.write(f"Fetching delivery order with DocNum: {options['id']}")
            records = client.fetch_by_docnum(options['id'])
        elif options['date']:
            # Fetch records for specific date
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
                self.stdout.write(f"Fetching delivery orders for date: {target_date}")
                records = client.fetch_by_date(target_date)
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid date format: {options['date']}. Use YYYY-MM-DD"))
                return
        else:
            # Fetch last N days
            days_back = options['days_back']
            self.stdout.write(f"Fetching delivery orders for last {days_back} days")
            records = client.sync_all(days_back=days_back)
        
        if not records:
            self.stdout.write(self.style.WARNING('No records fetched from API'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Fetched {len(records)} records from API'))
        
        # Step 2: FILTER (business rules)
        records = client._filter_records(records)
        self.stdout.write(f'After filtering: {len(records)} records')
        
        # Step 3: MAP to model format
        mapped = []
        for record in records:
            try:
                mapped_record = client._map_api_to_model(record)
                mapped.append(mapped_record)
            except Exception as e:
                logger.error(f"Error mapping record {record.get('DocNum', 'unknown')}: {e}")
                self.stdout.write(self.style.ERROR(f"Error mapping record: {e}"))
        
        self.stdout.write(f'Mapped {len(mapped)} records to model format')
        
        # Step 4: SERIALIZE for JSON (dates -> strings)
        serialized = serialize_for_json(mapped)
        
        # Validate serialized data before sending
        if serialized:
            # Check for required fields in first record
            first_record = serialized[0]
            required_fields = ['do_number', 'date', 'customer_code', 'customer_name']
            missing_fields = [field for field in required_fields if field not in first_record or first_record.get(field) is None]
            if missing_fields:
                self.stdout.write(self.style.WARNING(f"Warning: Some records may be missing required fields: {missing_fields}"))
        
        # Step 5: SAVE DATA
        if options['save_local']:
            # Save directly to local database
            self._save_to_database(mapped)
        elif not options['local_only']:
            # SEND to VPS via HTTP POST
            vps_url = getattr(settings, 'VPS_RECEIVE_URL', None)
            if not vps_url:
                # Use the production VPS URL
                vps_url = "https://do.junaidworld.com/api/sync/delivery-orders/"
            
            api_key = getattr(settings, 'VPS_API_KEY', '')
            if not api_key:
                self.stdout.write(self.style.ERROR('VPS_API_KEY not configured in settings'))
                return
            
            payload = {
                'records': serialized,
                'api_key': api_key,
                'sync_metadata': {
                    'sync_time': datetime.now().isoformat(),
                    'records_count': len(serialized),
                    'days_back': options.get('days_back'),
                    'date': options.get('date'),
                    'docnum': options.get('id'),
                }
            }
            
            # Validate we have records to send
            if not serialized:
                self.stdout.write(self.style.WARNING('No records to send to VPS'))
                return
            
            try:
                self.stdout.write(f'Sending {len(serialized)} records to VPS: {vps_url}')
                # Log first record structure for debugging
                if serialized:
                    logger.debug(f"Sample record keys: {list(serialized[0].keys())}")
                response = requests.post(
                    vps_url,
                    json=payload,
                    timeout=60,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
                
                result = response.json()
                if result.get('success'):
                    stats = result.get('stats', {})
                    self.stdout.write(self.style.SUCCESS(
                        f"[OK] Sync successful! Created: {stats.get('created', 0)}, "
                        f"Updated: {stats.get('updated', 0)}, "
                        f"Errors: {stats.get('errors', 0)}"
                    ))
                else:
                    error_msg = result.get('error', 'Unknown error')
                    self.stdout.write(self.style.ERROR(f"[ERROR] Sync failed: {error_msg}"))
                    logger.error(f"VPS sync failed: {error_msg}")
                    
            except requests.exceptions.HTTPError as e:
                # Capture response body for HTTP errors (400, 401, 500, etc.)
                error_details = f"{e}"
                try:
                    if e.response is not None:
                        error_body = e.response.text
                        error_details = f"{e} - Response: {error_body}"
                        # Try to parse JSON error response
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
        else:
            self.stdout.write(self.style.WARNING('--local-only mode: Skipping VPS push'))
            self.stdout.write(f'Would send {len(serialized)} records to VPS')
        
        # Step 6: LOG SUMMARY
        duration = (datetime.now() - start_time).total_seconds()
        self.stdout.write(self.style.SUCCESS(
            f'\n========= SYNC SUMMARY =========\n'
            f'Duration: {duration:.2f} seconds\n'
            f'Records fetched: {len(records)}\n'
            f'Records mapped: {len(mapped)}\n'
            f'Records serialized: {len(serialized)}\n'
            f'Mode: {"Local only (test)" if options["local_only"] else "Save local" if options["save_local"] else "Full sync"}\n'
            f'================================'
        ))
    
    def _save_to_database(self, mapped_records):
        """
        Save records directly to local database (bypasses HTTP)
        """
        stats = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'items_created': 0,
            'items_updated': 0,
            'items_deleted': 0
        }
        
        errors = []
        
        try:
            with transaction.atomic():
                # Get existing records by do_number
                do_numbers = [str(r.get('do_number', '')) for r in mapped_records if r.get('do_number')]
                existing_orders = DeliveryOrder.objects.filter(do_number__in=do_numbers)
                existing_map = {order.do_number: order for order in existing_orders}
                
                to_create = []
                to_update = []
                items_to_process = []  # (do_number, document_lines)
                
                for record in mapped_records:
                    do_number = str(record.get('do_number', ''))
                    if not do_number:
                        errors.append('Record missing do_number')
                        stats['errors'] += 1
                        continue
                    
                    # Extract document_lines for later processing
                    document_lines = record.pop('document_lines', [])
                    items_to_process.append((do_number, document_lines))
                    
                    # Handle empty strings for optional fields
                    for field in ['city', 'area', 'salesman', 'lpo', 'mobile_number']:
                        if record.get(field) == '':
                            record[field] = None
                    
                    if do_number in existing_map:
                        # Update existing record - only API-sourced fields
                        obj = existing_map[do_number]
                        update_fields = ['date', 'customer_code', 'customer_name', 'city', 'area', 'salesman', 'amount', 'lpo', 'mobile_number']
                        
                        for field in update_fields:
                            if field in record:
                                setattr(obj, field, record[field])
                        
                        to_update.append(obj)
                        stats['updated'] += 1
                    else:
                        # Create new record with defaults for app-managed fields
                        new_order = DeliveryOrder(
                            do_number=do_number,
                            date=record.get('date'),
                            customer_code=record.get('customer_code', ''),
                            customer_name=record.get('customer_name', ''),
                            city=record.get('city'),
                            area=record.get('area'),
                            salesman=record.get('salesman'),
                            amount=record.get('amount'),
                            lpo=record.get('lpo'),
                            mobile_number=record.get('mobile_number'),  # From BusinessPartner.Cellular
                            invoice_number=record.get('invoice_number'),  # Usually None
                            # App-managed fields use defaults:
                            status='Pending',  # Default status
                            driver=None,  # Default driver
                            vehicle=None,  # Default vehicle
                            delivery_date=None,  # Default delivery_date
                            received_date=None,  # Default received_date
                            salesman_mobile=None,  # Default salesman_mobile
                        )
                        to_create.append(new_order)
                        stats['created'] += 1
                
                # Bulk create new records
                if to_create:
                    DeliveryOrder.objects.bulk_create(to_create, batch_size=500)
                
                # Bulk update existing records
                if to_update:
                    update_fields = ['date', 'customer_code', 'customer_name', 'city', 'area', 'salesman', 'amount', 'lpo', 'mobile_number']
                    DeliveryOrder.objects.bulk_update(to_update, fields=update_fields, batch_size=500)
                
                # Process DeliveryItemWise records - only update if changed
                if items_to_process:
                    synced_do_numbers = [do_num for do_num, _ in items_to_process]
                    
                    # Get existing items for all synced DOs
                    existing_items = DeliveryItemWise.objects.filter(do_number__in=synced_do_numbers)
                    # Create a map: (do_number, item_code) -> DeliveryItemWise object
                    existing_items_map = {}
                    for item in existing_items:
                        key = (item.do_number, item.item_code)
                        existing_items_map[key] = item
                    
                    items_to_create = []
                    items_to_update = []
                    items_to_delete_keys = set(existing_items_map.keys())  # Start with all existing items
                    
                    for do_number, document_lines in items_to_process:
                        if not document_lines:
                            continue
                        
                        for line in document_lines:
                            item_code = str(line.get('ItemCode', ''))
                            if not item_code:
                                continue
                            
                            item_description = str(line.get('ItemDescription', ''))
                            
                            # Parse quantity
                            quantity = line.get('Quantity', 0)
                            try:
                                quantity = int(float(quantity)) if quantity else 0
                            except (ValueError, TypeError):
                                quantity = 0
                            
                            # Parse price
                            price = line.get('Price', 0)
                            try:
                                price = Decimal(str(price)) if price else Decimal('0.00')
                            except (InvalidOperation, ValueError, TypeError):
                                price = Decimal('0.00')
                            
                            key = (do_number, item_code)
                            
                            if key in existing_items_map:
                                # Item exists - check if it needs updating
                                existing_item = existing_items_map[key]
                                if (existing_item.item_description != item_description or
                                    existing_item.quantity != quantity or
                                    existing_item.price != price):
                                    # Update existing item
                                    existing_item.item_description = item_description
                                    existing_item.quantity = quantity
                                    existing_item.price = price
                                    items_to_update.append(existing_item)
                                # Remove from delete list since it still exists
                                items_to_delete_keys.discard(key)
                            else:
                                # New item - create it
                                items_to_create.append(
                                    DeliveryItemWise(
                                        do_number=do_number,
                                        item_code=item_code,
                                        item_description=item_description,
                                        quantity=quantity,
                                        price=price
                                    )
                                )
                    
                    # Delete items that are no longer in the API response
                    if items_to_delete_keys:
                        items_to_delete = [existing_items_map[key] for key in items_to_delete_keys]
                        deleted_count = len(items_to_delete)
                        DeliveryItemWise.objects.filter(id__in=[item.id for item in items_to_delete]).delete()
                        stats['items_deleted'] = deleted_count
                    
                    # Create new items
                    if items_to_create:
                        DeliveryItemWise.objects.bulk_create(items_to_create, batch_size=1000)
                        stats['items_created'] = len(items_to_create)
                    
                    # Update changed items
                    if items_to_update:
                        DeliveryItemWise.objects.bulk_update(items_to_update, ['item_description', 'quantity', 'price'], batch_size=1000)
                        stats['items_updated'] = len(items_to_update)
            
            self.stdout.write(self.style.SUCCESS(
                f"[OK] Saved to database! Created: {stats['created']}, "
                f"Updated: {stats['updated']}, "
                f"Items created: {stats['items_created']}, "
                f"Items updated: {stats.get('items_updated', 0)}, "
                f"Items deleted: {stats['items_deleted']}, "
                f"Errors: {stats['errors']}"
            ))
            
            if errors:
                self.stdout.write(self.style.WARNING(f"Warnings: {len(errors)} errors occurred"))
                for error in errors[:5]:  # Show first 5 errors
                    self.stdout.write(self.style.WARNING(f"  - {error}"))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error saving to database: {e}"))
            logger.error(f"Database save error: {e}", exc_info=True)
