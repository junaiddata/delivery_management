"""
SAP API Client for Delivery Orders
Handles communication with the internal SAP API endpoint.
"""
import requests
import re
from datetime import datetime, timedelta
from django.conf import settings
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)


def map_salesman_name(sap_salesman_name):
    """
    Map SAP salesman name to real name
    
    Args:
        sap_salesman_name: Salesman name from SAP (e.g., "B.MR.MUZAIN")
        
    Returns:
        Real salesman name (e.g., "MUZAIN") or original if no mapping found
    """
    if not sap_salesman_name:
        return None
    
    # Salesman name mapping: SAP format -> Real name
    salesman_mapping = {
        'B.MR.MUZAIN': 'MUZAIN',
        'D.RETAIL CUST DIP': 'DIP RETAIL',
        'B. MR.RAFIQ ABU- PROJ': 'RAFIQ ABUBAQAR',
        'A.MR.RASHID CONT': 'RASHID',
        'B.MR.PARTHIBAN': 'PARTHIBAN',
        'A.MR.SIYAB': 'SIYAB',
        'B.MR.NASHEER AHMAD': 'MR. NASHEER',
        'R.DEIRA 2': 'STORE DEIRA',
        'A.MR.RAFIQ': 'RAFIQ SHABBIR',
        'R.NAH': 'STORE NAH',
        'A.MR.RAFIQ ABU-TRD': 'RAFIQ ABUBAQAR',
        'A.MR.RASHID': 'RASHID',
        'R.ABUDHABI': 'STORE ABUDHABI',
        'R.STORES': 'STORE RAS',
        'A.MR.SIYAB CONT': 'SIYAB',
        '-No Sales Employee-': 'REPLACEMENT',
        'R.QUSAIS': 'STORE QUSAIS',
        'R.AJMAN': 'STORE AJMAN',
        'I.KRISHNAN': 'KRISHNAN',
        'B.MR.WASEEM': 'MERAJ',
        'E.DEIRA 1': 'STORE DEIRA 1',
        'ANISH DIP': 'ANISH',
        'D. ALABAMA': 'MERAJ',
        'A.MUSHARAF': 'MUSHARAF',
        'A.IBRAHIM': 'IBRAHIM',
        'B. MR.RAFIQ ABU. PROJ': 'RAFIQ ABUBAQAR',
        'A.DIP ADIL': 'ADIL',
        'A.DIP KADAR': 'KADAR',
        'A.DIP STEFFY': 'STEPHY',
        'A.DIP MUZAMMIL': 'MUZAMMIL',
        'A.KRISHNAN': 'KRISHNAN',
        'B.ANISH DIP': 'ANISH',
    }
    
    # Strip whitespace and try exact match first
    sap_name_clean = str(sap_salesman_name).strip()
    if sap_name_clean in salesman_mapping:
        return salesman_mapping[sap_name_clean]
    
    # If no exact match, return original (case-insensitive fallback)
    # This handles any variations we might have missed
    return sap_name_clean


def normalize_mobile_number(mobile_str):
    """
    Normalize mobile number to UAE format: 971xxxxxxxxx
    
    Handles various formats:
    - 971569913510 -> 971569913510
    - 971569913510 Mr Ahmad -> 971569913510
    - 056-1759979 -> 971561759979
    - 0564773409 -> 971564773409
    - 0522620761 Mr. Fraiju -> 971522620761
    - +971506419551 -> 971506419551
    - 971-50-7260198 -> 971507260198
    - 971 507114371 -> 971507114371
    - 0552948720/0564900266 -> 971552948720 (takes first)
    - 050-5260813 Ameen -> 971505260813
    
    Args:
        mobile_str: Raw mobile number string (can contain text, spaces, dashes, etc.)
        
    Returns:
        Normalized mobile number in format 971xxxxxxxxx or None if invalid
    """
    if not mobile_str:
        return None
    
    # Convert to string and strip whitespace
    mobile_str = str(mobile_str).strip()
    
    if not mobile_str:
        return None
    
    # If there's a slash, take only the first part
    if '/' in mobile_str:
        mobile_str = mobile_str.split('/')[0].strip()
    
    # Remove all non-digit characters except + at the start
    # First, check if it starts with +
    has_plus = mobile_str.startswith('+')
    
    # Extract only digits
    digits_only = re.sub(r'[^\d]', '', mobile_str)
    
    if not digits_only:
        return None
    
    # Handle different starting patterns
    if digits_only.startswith('971'):
        # Already has country code, just ensure it's 12 digits total
        normalized = digits_only[:12]  # 971 + 9 digits
        if len(normalized) == 12:
            return normalized
    elif digits_only.startswith('0'):
        # UAE local format (0XX...), replace 0 with 971
        if len(digits_only) >= 10:  # At least 0 + 9 digits
            normalized = '971' + digits_only[1:10]  # Remove leading 0, keep next 9 digits
            return normalized
    elif has_plus and digits_only.startswith('971'):
        # +971 format
        if len(digits_only) >= 12:
            return digits_only[:12]
    elif len(digits_only) == 9:
        # 9 digits without country code, add 971
        return '971' + digits_only
    elif len(digits_only) == 10 and digits_only.startswith('0'):
        # 10 digits starting with 0, replace 0 with 971
        return '971' + digits_only[1:]
    elif len(digits_only) >= 10:
        # More than 10 digits, might have country code embedded
        # Try to find 971 pattern
        if '971' in digits_only:
            idx = digits_only.index('971')
            remaining = digits_only[idx:]
            if len(remaining) >= 12:
                return remaining[:12]
        # Otherwise, if it's 12+ digits, take first 12
        if len(digits_only) >= 12:
            return digits_only[:12]
    
    # If we can't normalize it properly, return None
    return None


class SAPAPIClient:
    """Client for interacting with SAP Delivery Order API"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'SOURCE_API_URL', 'http://192.168.1.103/IntegrationApi/api/DeliveryOrder')
        self.timeout = getattr(settings, 'API_TIMEOUT', 30)
        self._cache = {}  # Cache for optimization
    
    def _make_request(self, payload, page_number=1):
        """
        Make API request to SAP endpoint with pagination support
        
        Args:
            payload: Dict with DocDate (YYYY-MM-DD) or DocNum
            page_number: Page number to fetch (default: 1)
            
        Returns:
            Dict with 'value' (list of records) and 'count' (total count) or empty dict on error
        """
        try:
            # Add pagination to payload
            request_payload = payload.copy()
            if page_number > 1:
                request_payload['pageNumber'] = page_number
            
            response = requests.post(
                self.base_url,
                json=request_payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Handle OData response format with pagination
            if isinstance(data, dict):
                records = data.get('value', [])
                total_count = int(data.get('odata.count', len(records)))
                return {
                    'value': records,
                    'count': total_count
                }
            elif isinstance(data, list):
                # Fallback: if API returns list directly
                return {
                    'value': data,
                    'count': len(data)
                }
            else:
                logger.warning(f"Unexpected API response format: {type(data)}")
                return {'value': [], 'count': 0}
                
        except requests.exceptions.Timeout:
            logger.error(f"API request timeout after {self.timeout}s")
            return {'value': [], 'count': 0}
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {'value': [], 'count': 0}
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            return {'value': [], 'count': 0}
    
    def _fetch_all_pages(self, payload, per_page=20):
        """
        Fetch all pages of results automatically
        
        Args:
            payload: Dict with DocDate (YYYY-MM-DD) or DocNum
            per_page: Number of records per page (default: 20)
            
        Returns:
            List of all delivery order records across all pages
        """
        all_records = []
        page_number = 1
        
        # Fetch first page to get total count
        first_page = self._make_request(payload, page_number=1)
        records = first_page.get('value', [])
        total_count = first_page.get('count', len(records))
        
        all_records.extend(records)
        
        # Calculate total pages
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        
        logger.info(f"Total records: {total_count}, Total pages: {total_pages}")
        
        # Fetch remaining pages
        for page in range(2, total_pages + 1):
            page_result = self._make_request(payload, page_number=page)
            page_records = page_result.get('value', [])
            all_records.extend(page_records)
            logger.info(f"Fetched page {page}/{total_pages}: {len(page_records)} records")
        
        return all_records
    
    def fetch_by_date(self, date):
        """
        Fetch delivery orders by document date (with pagination)
        
        Args:
            date: datetime.date or string in YYYY-MM-DD format
            
        Returns:
            List of delivery order records (all pages)
        """
        if isinstance(date, str):
            date_str = date
        else:
            date_str = date.strftime('%Y-%m-%d')
        
        payload = {"DocDate": date_str}
        logger.info(f"Fetching delivery orders for date: {date_str}")
        return self._fetch_all_pages(payload)
    
    def fetch_by_docnum(self, docnum):
        """
        Fetch single delivery order by document number
        
        Args:
            docnum: Document number (DocNum)
            
        Returns:
            List with single delivery order record or empty list
        """
        payload = {"DocNum": docnum}
        logger.info(f"Fetching delivery order by DocNum: {docnum}")
        result = self._make_request(payload)
        return result.get('value', [])
    
    def sync_all(self, days_back=3):
        """
        Main sync method: Fetch records for last N days
        
        Args:
            days_back: Number of days to look back (default: 3)
            
        Returns:
            List of unique delivery order records (deduplicated by DocNum)
        """
        all_records = []
        seen_docnums = set()
        
        # Fetch records for each day
        today = datetime.now().date()
        for i in range(days_back):
            target_date = today - timedelta(days=i)
            records = self.fetch_by_date(target_date)
            
            # Deduplicate by DocNum
            for record in records:
                docnum = str(record.get('DocNum', ''))
                if docnum and docnum not in seen_docnums:
                    seen_docnums.add(docnum)
                    all_records.append(record)
        
        logger.info(f"Fetched {len(all_records)} unique delivery orders from last {days_back} days")
        return all_records
    
    def _filter_records(self, records, exclude_one_prefix=False):
        """
        Apply business filters to records
        
        Args:
            records: List of API records
            exclude_one_prefix: If True, filter to exclude DOs starting with "1"
                              If False (default), filter to only include DOs starting with "1"
            
        Returns:
            Filtered list of records
        """
        filtered = []
        for record in records:
            docnum = str(record.get('DocNum', ''))
            if not docnum:
                continue
                
            if exclude_one_prefix:
                # Filter: Only sync DOs NOT starting with "1"
                if not docnum.startswith('1'):
                    filtered.append(record)
                else:
                    logger.debug(f"Skipping DO {docnum} - starts with '1' (excluded)")
            else:
                # Filter: Only sync DOs where do_number (DocNum) starts with "1"
                if docnum.startswith('1'):
                    filtered.append(record)
                else:
                    logger.debug(f"Skipping DO {docnum} - does not start with '1'")
        
        filter_desc = "DOs NOT starting with '1'" if exclude_one_prefix else "DOs starting with '1'"
        logger.info(f"Filtered {len(records)} records to {len(filtered)} ({filter_desc})")
        return filtered
    
    def _map_api_to_model(self, api_record):
        """
        Transform API response to Django model format
        
        Args:
            api_record: Dict from API response
            
        Returns:
            Dict with model fields mapped from API fields
        """
        # Extract sales person name
        sales_person = api_record.get('SalesPerson', {})
        sales_person_name_raw = sales_person.get('SalesEmployeeName', '') if isinstance(sales_person, dict) else ''
        
        # Map SAP salesman name to real name
        sales_person_name = map_salesman_name(sales_person_name_raw)
        
        # Get customer_code for lookup
        customer_code = str(api_record.get('CardCode', ''))
        
        # First, try to get mobile number from Customer model (from Excel)
        mobile_number = None
        try:
            from orders.models import Customer
            customer = Customer.objects.filter(customer_code=customer_code).first()
            if customer and customer.mobile_number:
                mobile_number = normalize_mobile_number(customer.mobile_number)
                logger.debug(f"Found mobile number in Customer model for {customer_code}: {mobile_number}")
        except Exception as e:
            logger.warning(f"Error looking up Customer model for {customer_code}: {e}")
        
        # If not found in Customer model, fall back to API fields
        if not mobile_number:
            business_partner = api_record.get('BusinessPartner', {})
            mobile_number_raw = None
            
            if isinstance(business_partner, dict):
                # Try Cellular first, then Phone1, then Phone2
                mobile_number_raw = (
                    business_partner.get('Cellular') or 
                    business_partner.get('Phone1') or 
                    business_partner.get('Phone2')
                )
            
            # Normalize mobile number to UAE format
            mobile_number = normalize_mobile_number(mobile_number_raw) if mobile_number_raw else None
            if mobile_number:
                logger.debug(f"Using mobile number from API for {customer_code}: {mobile_number}")
        
        # Extract document lines
        document_lines = api_record.get('DocumentLines', [])
        
        # Get customer name - special handling for "DEBIT CUSTOMER ( CASH )"
        customer_name_raw = str(api_record.get('CardName', ''))
        if customer_name_raw == "DEBIT CUSTOMER ( CASH )":
            # Use Comments field instead
            comments = api_record.get('Comments', '')
            customer_name = str(comments) if comments else customer_name_raw
            logger.debug(f"Replaced 'DEBIT CUSTOMER ( CASH )' with Comments: {customer_name}")
        else:
            customer_name = customer_name_raw
        
        # Map API fields to model fields
        mapped = {
            'do_number': str(api_record.get('DocNum', '')),
            'date': self._parse_date(api_record.get('DocDate')),
            'customer_code': str(api_record.get('CardCode', '')),
            'customer_name': customer_name,
            'city': str(api_record.get('U_TenX_City', '') or ''),
            'area': str(api_record.get('U_TenX_Area', '') or ''),
            'salesman': sales_person_name,
            'amount': self._parse_decimal(api_record.get('DocTotal', 0)),
            'lpo': str(api_record.get('NumAtCard', '') or ''),
            'mobile_number': mobile_number,
            'invoice_number': None,  # Leave empty, set manually later
            'document_lines': document_lines,  # For processing items separately
        }
        
        return mapped
    
    def _parse_date(self, date_value):
        """
        Parse date from various formats
        
        Args:
            date_value: Date string or None
            
        Returns:
            datetime.date or None
        """
        if not date_value:
            return None
        
        if isinstance(date_value, str):
            # Try common date formats
            formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt).date()
                except ValueError:
                    continue
            logger.warning(f"Could not parse date: {date_value}")
            return None
        
        return date_value
    
    def _parse_decimal(self, value):
        """
        Parse decimal value safely
        
        Args:
            value: Numeric value or string
            
        Returns:
            Decimal or None
        """
        if value is None or value == '':
            return None
        
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            logger.warning(f"Could not parse decimal: {value}")
            return None
    
    def fetch_cancelled_orders(self, cancel_status):
        """
        Fetch cancelled delivery orders by CancelStatus
        
        Args:
            cancel_status: CancelStatus value ("csCancellation" or "csYes")
            
        Returns:
            List of cancelled delivery order records (all pages)
        """
        payload = {"CancelStatus": cancel_status}
        logger.info(f"Fetching cancelled delivery orders with CancelStatus: {cancel_status}")
        return self._fetch_all_pages(payload)
    
    def fetch_all_cancelled_orders(self):
        """
        Fetch all cancelled delivery orders (both csCancellation and csYes)
        
        Returns:
            List of all cancelled delivery order records (deduplicated by DocNum)
        """
        all_cancelled = []
        seen_docnums = set()
        
        # Fetch orders with csCancellation status
        logger.info("Fetching cancelled orders with CancelStatus: csCancellation")
        cancellation_records = self.fetch_cancelled_orders("csCancellation")
        
        # Fetch orders with csYes status
        logger.info("Fetching cancelled orders with CancelStatus: csYes")
        csyes_records = self.fetch_cancelled_orders("csYes")
        
        # Combine and deduplicate by DocNum
        for record in cancellation_records + csyes_records:
            docnum = str(record.get('DocNum', ''))
            if docnum and docnum not in seen_docnums:
                seen_docnums.add(docnum)
                all_cancelled.append(record)
        
        logger.info(f"Found {len(all_cancelled)} unique cancelled delivery orders")
        return all_cancelled
