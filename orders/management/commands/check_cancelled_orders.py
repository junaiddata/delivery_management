"""
Django management command to check and update cancelled delivery orders from SAP API to VPS
Only updates VPS database - does not touch local database
"""
import logging
import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from orders.api_client import SAPAPIClient

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check for cancelled delivery orders from SAP API and update VPS database to Cancelled status'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually updating the VPS',
        )
        parser.add_argument(
            '--local',
            action='store_true',
            help='Test mode: use local URL instead of VPS (http://localhost:8000/api/sync/delivery-orders/)',
        )
    
    def handle(self, *args, **options):
        start_time = datetime.now()
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('Starting cancelled delivery orders check...'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made to VPS"))
        
        # Initialize API client
        client = SAPAPIClient()
        
        # Fetch only last 5 pages of cancelled orders from API
        self.stdout.write("Fetching last 5 pages of cancelled orders from API...")
        try:
            cancelled_records = self._fetch_last_pages_cancelled_orders(client)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching cancelled orders: {e}"))
            logger.error(f"Error fetching cancelled orders: {e}", exc_info=True)
            return
        
        if not cancelled_records:
            self.stdout.write(self.style.WARNING("No cancelled orders found in API"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Found {len(cancelled_records)} cancelled orders in API"))
        
        # Extract DocNum values from cancelled records and filter by do_number > 126000000
        cancelled_docnums = []
        for record in cancelled_records:
            docnum = str(record.get('DocNum', '')).strip()
            if docnum:
                try:
                    # Convert to integer for comparison
                    docnum_int = int(docnum)
                    if docnum_int > 126000000:
                        cancelled_docnums.append(docnum)
                except ValueError:
                    # If not a valid integer, skip it
                    logger.debug(f"Skipping non-numeric DocNum: {docnum}")
                    continue
        
        if not cancelled_docnums:
            self.stdout.write(self.style.WARNING("No cancelled orders found with do_number > 126000000"))
            return
        
        self.stdout.write(f"Found {len(cancelled_docnums)} cancelled DOs with do_number > 126000000")
        
        # Display summary
        self.stdout.write(f"\n========= SUMMARY =========")
        self.stdout.write(f"Total cancelled orders in API: {len(cancelled_records)}")
        self.stdout.write(f"Cancelled DOs with do_number > 126000000: {len(cancelled_docnums)}")
        
        if len(cancelled_docnums) <= 20:
            self.stdout.write(f"\nDOs that will be updated to 'Cancelled' status on VPS:")
            for docnum in sorted(cancelled_docnums):
                if dry_run:
                    self.stdout.write(f"  - DO {docnum}: -> 'Cancelled'")
                else:
                    self.stdout.write(f"  - DO {docnum}: -> 'Cancelled'")
        else:
            self.stdout.write(f"\nFirst 20 DOs that will be updated:")
            for docnum in sorted(cancelled_docnums)[:20]:
                self.stdout.write(f"  - DO {docnum}")
            self.stdout.write(f"  ... and {len(cancelled_docnums) - 20} more")
        
        # Send status updates to VPS
        if not dry_run:
            target = "local server" if options.get('local') else "VPS"
            self.stdout.write(f"\nSending cancelled status updates to {target}...")
            vps_updated = self._send_cancelled_status_to_vps(cancelled_docnums, use_local=options.get('local'))
            
            if vps_updated:
                self.stdout.write(self.style.SUCCESS(
                    f"[OK] Successfully updated {vps_updated} delivery orders to 'Cancelled' status on {target}"
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"[ERROR] Failed to update {target} (check logs for details)"
                ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n[OK] Would update {len(cancelled_docnums)} delivery orders to 'Cancelled' status on VPS"
            ))
        
        # Log summary
        duration = (datetime.now() - start_time).total_seconds()
        self.stdout.write(self.style.SUCCESS(
            f'\n========= CHECK SUMMARY =========\n'
            f'Duration: {duration:.2f} seconds\n'
            f'Cancelled orders in API: {len(cancelled_records)}\n'
            f'DOs with do_number > 126000000: {len(cancelled_docnums)}\n'
            f'Updated: {("N/A (dry-run)" if dry_run else vps_updated)}\n'
            f'Mode: {"Dry run" if dry_run else "Live update"}\n'
            f'================================'
        ))
    
    def _fetch_last_pages_cancelled_orders(self, client, last_pages=5):
        """
        Fetch only the last N pages of cancelled orders (for both CancelStatus values)
        
        Args:
            client: SAPAPIClient instance
            last_pages: Number of last pages to fetch (default: 5)
            
        Returns:
            List of cancelled delivery order records from last pages
        """
        all_cancelled = []
        seen_docnums = set()
        per_page = 20
        
        # Fetch for both CancelStatus values
        for cancel_status in ["csCancellation", "csYes"]:
            payload = {"CancelStatus": cancel_status}
            logger.info(f"Fetching last {last_pages} pages for CancelStatus: {cancel_status}")
            
            # Get first page to know total pages
            first_page = client._make_request(payload, page_number=1)
            records = first_page.get('value', [])
            total_count = first_page.get('count', len(records))
            
            # Calculate total pages
            total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
            
            if total_pages == 0:
                logger.info(f"No pages found for CancelStatus: {cancel_status}")
                continue
            
            # Calculate which pages to fetch (last N pages)
            start_page = max(1, total_pages - last_pages + 1)
            end_page = total_pages
            
            self.stdout.write(f"  CancelStatus {cancel_status}: Total pages: {total_pages}, Fetching pages {start_page} to {end_page}")
            
            # Fetch only the last N pages
            for page in range(start_page, end_page + 1):
                page_result = client._make_request(payload, page_number=page)
                page_records = page_result.get('value', [])
                
                # Deduplicate by DocNum
                for record in page_records:
                    docnum = str(record.get('DocNum', ''))
                    if docnum and docnum not in seen_docnums:
                        seen_docnums.add(docnum)
                        all_cancelled.append(record)
                
                logger.info(f"Fetched page {page}/{total_pages} for {cancel_status}: {len(page_records)} records")
        
        logger.info(f"Found {len(all_cancelled)} unique cancelled delivery orders from last {last_pages} pages")
        return all_cancelled
    
    def _send_cancelled_status_to_vps(self, cancelled_docnums, use_local=False):
        """
        Send cancelled status updates to VPS or local server
        
        Args:
            cancelled_docnums: List of DO numbers to mark as cancelled
            use_local: If True, use local URL instead of VPS
            
        Returns:
            Number of successfully updated records
        """
        if not cancelled_docnums:
            return 0
        
        if use_local:
            vps_url = "http://localhost:8000/api/sync/delivery-orders/"
            self.stdout.write(f"Using LOCAL URL: {vps_url}")
        else:
            vps_url = getattr(settings, 'VPS_RECEIVE_URL', None)
            if not vps_url:
                vps_url = "https://do.junaidworld.com/api/sync/delivery-orders/"
        
        api_key = getattr(settings, 'VPS_API_KEY', '')
        if not api_key:
            logger.error("VPS_API_KEY not configured in settings")
            self.stdout.write(self.style.ERROR("VPS_API_KEY not configured - cannot update VPS"))
            return 0
        
        # Prepare records with status field (only do_number and status)
        records = []
        for docnum in cancelled_docnums:
            records.append({
                'do_number': docnum,
                'status': 'Cancelled'  # Include status in payload
            })
        
        payload = {
            'records': records,
            'api_key': api_key,
            'sync_metadata': {
                'sync_type': 'status_update',
                'sync_time': datetime.now().isoformat(),
                'records_count': len(records),
                'status': 'Cancelled'
            }
        }
        
        try:
            self.stdout.write(f"Sending {len(records)} status updates to: {vps_url}")
            response = requests.post(
                vps_url,
                json=payload,
                timeout=60,
                headers={'Content-Type': 'application/json'}
            )
            # Check status code first
            if response.status_code != 200:
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get('error', f'HTTP {response.status_code}')
                except:
                    error_msg = f'HTTP {response.status_code}: {response.text[:200]}'
                logger.error(f"VPS returned error: {error_msg}")
                self.stdout.write(self.style.ERROR(f"VPS error: {error_msg}"))
                return 0
            
            result = response.json()
            if result.get('success'):
                stats = result.get('stats', {})
                updated_count = stats.get('updated', 0)
                logger.info(f"VPS status update successful: {updated_count} records updated")
                return updated_count
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"VPS status update failed: {error_msg}")
                self.stdout.write(self.style.ERROR(f"VPS error: {error_msg}"))
                return 0
                
        except requests.exceptions.HTTPError as e:
            # Try to get error details from response
            try:
                error_detail = e.response.json() if e.response else {}
                error_msg = error_detail.get('error', str(e))
                logger.error(f"VPS HTTP error: {error_msg}")
                self.stdout.write(self.style.ERROR(f"VPS HTTP error: {error_msg}"))
            except:
                logger.error(f"VPS HTTP error: {e}")
                self.stdout.write(self.style.ERROR(f"VPS HTTP error: {e}"))
            return 0
        except requests.exceptions.RequestException as e:
            logger.error(f"VPS status update error: {e}")
            self.stdout.write(self.style.ERROR(f"Error connecting to VPS: {e}"))
            return 0
        except Exception as e:
            logger.error(f"Unexpected error sending to VPS: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"Unexpected error: {e}"))
            return 0
