"""
Standalone script to sync cancelled delivery orders from SAP API to VPS
Can be run directly: python sync_cancelled_orders.py
Or imported and called from anywhere
"""
import os
import sys
import django
import logging
import requests
from datetime import datetime

# Setup Django environment
if __name__ == "__main__":
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'delivery_management.settings')
    django.setup()

from django.conf import settings
from orders.api_client import SAPAPIClient

# Configure logging
logger = logging.getLogger(__name__)


def sync_cancelled_orders(use_local=False):
    """
    Sync cancelled delivery orders from SAP API to VPS
    
    Args:
        use_local: If True, use local URL instead of VPS
        
    Returns:
        dict with 'success', 'updated_count', 'message'
    """
    try:
        # Initialize API client
        client = SAPAPIClient()
        
        # Fetch only last 5 pages of cancelled orders from API
        logger.info("Fetching last 5 pages of cancelled orders from API...")
        cancelled_records = _fetch_last_pages_cancelled_orders(client)
        
        if not cancelled_records:
            return {
                'success': False,
                'updated_count': 0,
                'message': 'No cancelled orders found in API'
            }
        
        # Extract DocNum values from cancelled records and filter by do_number > 126000000
        cancelled_docnums = []
        for record in cancelled_records:
            docnum = str(record.get('DocNum', '')).strip()
            if docnum:
                try:
                    docnum_int = int(docnum)
                    if docnum_int > 126000000:
                        cancelled_docnums.append(docnum)
                except ValueError:
                    logger.debug(f"Skipping non-numeric DocNum: {docnum}")
                    continue
        
        if not cancelled_docnums:
            return {
                'success': False,
                'updated_count': 0,
                'message': 'No cancelled orders found with do_number > 126000000'
            }
        
        # Send status updates to VPS
        updated_count = _send_cancelled_status_to_vps(cancelled_docnums, use_local=use_local)
        
        if updated_count > 0:
            return {
                'success': True,
                'updated_count': updated_count,
                'message': f'Updated {updated_count}'
            }
        else:
            return {
                'success': False,
                'updated_count': 0,
                'message': 'Failed to update VPS (check logs for details)'
            }
            
    except Exception as e:
        logger.error(f"Error syncing cancelled orders: {e}", exc_info=True)
        return {
            'success': False,
            'updated_count': 0,
            'message': f'Error: {str(e)}'
        }


def _fetch_last_pages_cancelled_orders(client, last_pages=5):
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
        
        logger.info(f"CancelStatus {cancel_status}: Total pages: {total_pages}, Fetching pages {start_page} to {end_page}")
        
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


def _send_cancelled_status_to_vps(cancelled_docnums, use_local=False):
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
    else:
        vps_url = getattr(settings, 'VPS_RECEIVE_URL', None)
        if not vps_url:
            vps_url = "https://do.junaidworld.com/api/sync/delivery-orders/"
    
    api_key = getattr(settings, 'VPS_API_KEY', '')
    if not api_key:
        logger.error("VPS_API_KEY not configured in settings")
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
        logger.info(f"Sending {len(records)} status updates to: {vps_url}")
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
            return 0
            
    except requests.exceptions.RequestException as e:
        logger.error(f"VPS status update error: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error sending to VPS: {e}", exc_info=True)
        return 0


if __name__ == "__main__":
    # Run when executed directly
    print("Syncing cancelled orders...")
    result = sync_cancelled_orders()
    print(result['message'])
    sys.exit(0 if result['success'] else 1)
