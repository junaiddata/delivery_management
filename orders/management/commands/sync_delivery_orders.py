"""
Django management command to sync delivery orders from SAP API to cloud VPS
"""
import json
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from orders.api_client import SAPAPIClient
from orders.sync_services import sync_delivery_orders_core

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
        records_count = mapped_count = serialized_count = 0
        
        self.stdout.write(self.style.SUCCESS('Starting delivery order sync...'))
        
        if options['save_local']:
            # Use core sync (VPS-centric path)
            try:
                result = sync_delivery_orders_core(
                    days_back=options['days_back'],
                    specific_date=options.get('date'),
                    docnum=options.get('id')
                )
                stats = result.get('stats', {})
                records_count = result.get('records_fetched', 0)
                self.stdout.write(self.style.SUCCESS(
                    f"[OK] Saved to database! Created: {stats.get('created', 0)}, "
                    f"Updated: {stats.get('updated', 0)}, "
                    f"Items created: {stats.get('items_created', 0)}, "
                    f"Items updated: {stats.get('items_updated', 0)}, "
                    f"Errors: {stats.get('errors', 0)}"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[ERROR] Sync failed: {e}"))
                logger.error(f"Sync failed: {e}", exc_info=True)
        elif not options['local_only']:
            # Push to VPS (legacy path) - need to fetch, filter, map, serialize
            client = SAPAPIClient()
            records = []
            if options['id']:
                self.stdout.write(f"Fetching delivery order with DocNum: {options['id']}")
                records = client.fetch_by_docnum(options['id'])
            elif options['date']:
                try:
                    target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
                    self.stdout.write(f"Fetching delivery orders for date: {target_date}")
                    records = client.fetch_by_date(target_date)
                except ValueError:
                    self.stdout.write(self.style.ERROR(f"Invalid date format: {options['date']}. Use YYYY-MM-DD"))
                    return
            else:
                days_back = options['days_back']
                self.stdout.write(f"Fetching delivery orders for last {days_back} days")
                records = client.sync_all(days_back=days_back)

            if not records:
                self.stdout.write(self.style.WARNING('No records fetched from API'))
                return

            records = client._filter_records(records)
            mapped = []
            for record in records:
                try:
                    mapped.append(client._map_api_to_model(record))
                except Exception as e:
                    logger.error(f"Error mapping record {record.get('DocNum', 'unknown')}: {e}")
            serialized = serialize_for_json(mapped)
            records_count = len(records)
            mapped_count = len(mapped)
            serialized_count = len(serialized)
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
            # local_only: fetch for display only
            client = SAPAPIClient()
            records = []
            if options['id']:
                records = client.fetch_by_docnum(options['id'])
            elif options['date']:
                try:
                    target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
                    records = client.fetch_by_date(target_date)
                except ValueError:
                    pass
            else:
                records = client.sync_all(days_back=options['days_back'])
            records = client._filter_records(records) if records else []
            mapped = []
            for r in records:
                try:
                    mapped.append(client._map_api_to_model(r))
                except Exception:
                    pass
            serialized = serialize_for_json(mapped) if mapped else []
            records_count = len(records)
            mapped_count = len(mapped)
            serialized_count = len(serialized)
            self.stdout.write(self.style.WARNING('--local-only mode: Skipping VPS push'))
            self.stdout.write(f'Would send {serialized_count} records to VPS')
        
        # LOG SUMMARY
        duration = (datetime.now() - start_time).total_seconds()
        mode_str = "Local only (test)" if options["local_only"] else "Save local" if options["save_local"] else "Full sync"
        summary = f'\n========= SYNC SUMMARY =========\nDuration: {duration:.2f} seconds\nRecords fetched: {records_count}\nRecords mapped: {mapped_count}\nRecords serialized: {serialized_count}\nMode: {mode_str}\n================================'
        self.stdout.write(self.style.SUCCESS(summary))
    
