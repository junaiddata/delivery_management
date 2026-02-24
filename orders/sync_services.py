"""
Core sync services for VPS-centric sync.
All sync logic runs here; management commands and Settings page call these functions.
"""
import logging
import logging.handlers
import uuid
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction

from orders.api_client import SAPAPIClient
from orders.models import DeliveryOrder, DeliveryItemWise, CreditPayment


# Per-entity loggers with RotatingFileHandler (10MB, 5 backups)
LOG_DIR = getattr(settings, 'LOG_DIR', None)
if LOG_DIR is None:
    from pathlib import Path
    LOG_DIR = Path(settings.BASE_DIR) / "logs"

try:
    LOG_DIR.mkdir(exist_ok=True)
except (OSError, PermissionError):
    pass

_ENTITY_LOGGERS = {}


def _get_entity_logger(entity_name):
    """Get or create a per-entity logger with RotatingFileHandler."""
    global _ENTITY_LOGGERS
    if entity_name in _ENTITY_LOGGERS:
        return _ENTITY_LOGGERS[entity_name]

    logger = logging.getLogger(f'orders.sync_{entity_name}')
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    try:
        log_path = LOG_DIR / f"sync_{entity_name}.log"
        handler = logging.handlers.RotatingFileHandler(
            str(log_path),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8',
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
    except (OSError, PermissionError):
        pass

    _ENTITY_LOGGERS[entity_name] = logger
    return logger


# --- Invoice helpers (from sync_do_invoices) ---

def _generate_random_invoice():
    return f"C{uuid.uuid4().hex[:12].upper()}"


def _normalize_invoice(invoice_value):
    if invoice_value is None:
        return _generate_random_invoice()
    invoice_str = str(invoice_value).strip()
    if not invoice_str or invoice_str.upper() == 'NIL':
        return _generate_random_invoice()
    return invoice_str


def _make_invoice_unique(base_invoice, current_order):
    if current_order.invoice_number:
        current_inv = current_order.invoice_number
        if current_inv == base_invoice:
            if not DeliveryOrder.objects.exclude(pk=current_order.pk).filter(invoice_number=base_invoice).exists():
                return base_invoice
        elif current_inv.startswith(base_invoice + '-'):
            if not DeliveryOrder.objects.exclude(pk=current_order.pk).filter(invoice_number=current_inv).exists():
                return current_inv

    if not DeliveryOrder.objects.exclude(pk=current_order.pk).filter(invoice_number=base_invoice).exists():
        return base_invoice

    for suffix_letter in range(ord('A'), ord('Z') + 1):
        candidate = f"{base_invoice}-{chr(suffix_letter)}"
        if not DeliveryOrder.objects.exclude(pk=current_order.pk).filter(invoice_number=candidate).exists():
            return candidate

    return _generate_random_invoice()


# --- Shared save function ---

def save_delivery_order_records(records, sync_metadata=None):
    """
    Save delivery order records to database. Used by sync_receive and core sync functions.

    Args:
        records: List of dicts (model format or POST payload format)
        sync_metadata: Optional dict with update_only, sync_type, etc.

    Returns:
        dict with created, updated, errors, items_created, items_updated
    """
    sync_metadata = sync_metadata or {}
    stats = {
        'created': 0,
        'updated': 0,
        'errors': 0,
        'items_created': 0,
        'items_updated': 0
    }
    errors = []

    has_status_updates = any(
        isinstance(r, dict) and 'status' in r and r.get('status') for r in records
    )
    has_invoice_in_payload = any(
        isinstance(r, dict) and 'invoice_number' in r
        and r.get('invoice_number') is not None
        and str(r.get('invoice_number')).strip() != ''
        for r in records
    )
    status_only_mode = all(
        isinstance(r, dict)
        and set(r.keys()).issubset({'do_number', 'status', 'document_lines'})
        and r.get('do_number')
        and r.get('status')
        for r in records
    )

    with transaction.atomic():
        do_numbers = [str(r.get('do_number', '')) for r in records if r.get('do_number')]
        existing_orders = DeliveryOrder.objects.filter(do_number__in=do_numbers)
        existing_map = {order.do_number: order for order in existing_orders}

        to_create = []
        to_update = []
        items_to_process = []

        for record in records:
            do_number = str(record.get('do_number', ''))
            if not do_number:
                errors.append('Record missing do_number')
                stats['errors'] += 1
                continue

            if status_only_mode:
                if do_number in existing_map:
                    obj = existing_map[do_number]
                    obj.status = record.get('status')
                    to_update.append(obj)
                    stats['updated'] += 1
                continue

            document_lines = record.pop('document_lines', [])
            items_to_process.append((do_number, document_lines))

            date_str = record.get('date')
            if date_str:
                try:
                    record['date'] = datetime.strptime(date_str, '%Y-%m-%d').date() if isinstance(date_str, str) else date_str
                except (ValueError, TypeError):
                    errors.append(f'Invalid date for DO {do_number}: {date_str}')
                    record['date'] = None

            amount_str = record.get('amount')
            if amount_str:
                try:
                    record['amount'] = Decimal(str(amount_str))
                except (InvalidOperation, ValueError, TypeError):
                    record['amount'] = None

            for field in ['city', 'area', 'salesman', 'lpo', 'mobile_number']:
                if record.get(field) == '':
                    record[field] = None

            if do_number in existing_map:
                obj = existing_map[do_number]
                update_fields = ['date', 'customer_code', 'customer_name', 'city', 'area', 'salesman', 'amount', 'lpo', 'mobile_number']
                if 'status' in record and record.get('status'):
                    update_fields.append('status')
                if 'invoice_number' in record:
                    invoice_val = record.get('invoice_number')
                    if invoice_val is not None and str(invoice_val).strip() != '':
                        setattr(obj, 'invoice_number', str(invoice_val).strip())
                    else:
                        setattr(obj, 'invoice_number', None)
                    obj._needs_invoice_update = True
                for field in update_fields:
                    if field in record:
                        setattr(obj, field, record[field])
                to_update.append(obj)
                stats['updated'] += 1
            else:
                if sync_metadata.get('update_only', False):
                    errors.append(f'DO {do_number} not found (update-only mode)')
                    stats['errors'] += 1
                    continue
                if 'status' in record and record.get('status') and not record.get('date'):
                    continue
                status_value = record.get('status', 'Pending')
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
                    mobile_number=record.get('mobile_number'),
                    invoice_number=record.get('invoice_number'),
                    status=status_value,
                    driver=None,
                    vehicle=None,
                    delivery_date=None,
                    received_date=None,
                    salesman_mobile=None,
                )
                to_create.append(new_order)
                stats['created'] += 1

        if to_create:
            DeliveryOrder.objects.bulk_create(to_create, batch_size=500)

        if to_update:
            base_update_fields = ['date', 'customer_code', 'customer_name', 'city', 'area', 'salesman', 'amount', 'lpo', 'mobile_number']
            if status_only_mode:
                fields_to_update = ['status']
            else:
                fields_to_update = base_update_fields.copy()
                if has_status_updates:
                    fields_to_update.append('status')
                if has_invoice_in_payload or any(
                    hasattr(obj, '_needs_invoice_update') and obj._needs_invoice_update for obj in to_update
                ):
                    fields_to_update.append('invoice_number')
            DeliveryOrder.objects.bulk_update(to_update, fields=fields_to_update, batch_size=500)

        # Process DeliveryItemWise - bulk_create/bulk_update OUTSIDE the per-DO loop
        if items_to_process and not status_only_mode:
            synced_do_numbers = [do_num for do_num, _ in items_to_process]
            existing_items = DeliveryItemWise.objects.filter(do_number__in=synced_do_numbers)
            existing_items_map = {(item.do_number, item.item_code): item for item in existing_items}

            items_to_create = []
            items_to_update = []

            for do_number, document_lines in items_to_process:
                if not document_lines:
                    continue
                for line in document_lines:
                    item_code = str(line.get('ItemCode', ''))
                    if not item_code:
                        continue
                    item_description = str(line.get('ItemDescription', ''))
                    quantity = line.get('Quantity', 0)
                    try:
                        quantity = int(float(quantity)) if quantity else 0
                    except (ValueError, TypeError):
                        quantity = 0
                    price = line.get('Price', 0)
                    try:
                        price = Decimal(str(price)) if price else Decimal('0.00')
                    except (InvalidOperation, ValueError, TypeError):
                        price = Decimal('0.00')

                    key = (do_number, item_code)
                    if key in existing_items_map:
                        existing_item = existing_items_map[key]
                        if (existing_item.item_description != item_description or
                                existing_item.quantity != quantity or
                                existing_item.price != price):
                            existing_item.item_description = item_description
                            existing_item.quantity = quantity
                            existing_item.price = price
                            items_to_update.append(existing_item)
                    else:
                        items_to_create.append(
                            DeliveryItemWise(
                                do_number=do_number,
                                item_code=item_code,
                                item_description=item_description,
                                quantity=quantity,
                                price=price
                            )
                        )

            if items_to_create:
                DeliveryItemWise.objects.bulk_create(items_to_create, batch_size=1000)
                stats['items_created'] = len(items_to_create)
            if items_to_update:
                DeliveryItemWise.objects.bulk_update(items_to_update, ['item_description', 'quantity', 'price'], batch_size=1000)
                stats['items_updated'] = len(items_to_update)

    stats['errors_list'] = errors
    return stats


# --- Core sync functions ---

def sync_delivery_orders_core(days_back=3, specific_date=None, docnum=None):
    """Sync delivery orders (DOs starting with '1') from API to local DB."""
    logger = _get_entity_logger('orders')
    start = datetime.now()
    logger.info(f"Starting sync_delivery_orders_core: days_back={days_back}, date={specific_date}, docnum={docnum}")

    try:
        client = SAPAPIClient()
        if docnum:
            records = client.fetch_by_docnum(docnum)
        elif specific_date:
            if isinstance(specific_date, str):
                specific_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
            records = client.fetch_by_date(specific_date)
        else:
            records = client.sync_all(days_back=days_back)

        records = client._filter_records(records, exclude_one_prefix=False)
        mapped = []
        for record in records:
            try:
                mapped.append(client._map_api_to_model(record))
            except Exception as e:
                logger.error(f"Error mapping record {record.get('DocNum', 'unknown')}: {e}")

        if not mapped:
            logger.info("No records to save")
            return {'stats': {'created': 0, 'updated': 0, 'errors': 0, 'items_created': 0, 'items_updated': 0}, 'duration': 0}

        stats = save_delivery_order_records(mapped, {})
        duration = (datetime.now() - start).total_seconds()
        logger.info(f"sync_delivery_orders_core completed: created={stats['created']}, updated={stats['updated']}, "
                   f"items_created={stats['items_created']}, items_updated={stats['items_updated']}, "
                   f"errors={stats['errors']}, duration={duration:.2f}s")
        return {'stats': stats, 'duration': duration, 'records_fetched': len(records)}
    except Exception as e:
        logger.error(f"sync_delivery_orders_core failed: {e}", exc_info=True)
        raise


def sync_non_one_delivery_orders_core(days_back=3, specific_date=None, from_date=None, to_date=None, docnum=None):
    """Sync delivery orders NOT starting with '1' from API to local DB."""
    logger = _get_entity_logger('non_one')
    start = datetime.now()
    logger.info(f"Starting sync_non_one_delivery_orders_core: days_back={days_back}, date={specific_date}, "
                f"from={from_date}, to={to_date}, docnum={docnum}")

    try:
        client = SAPAPIClient()
        if docnum:
            records = client.fetch_by_docnum(docnum)
        elif from_date and to_date:
            if isinstance(from_date, str):
                from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            if isinstance(to_date, str):
                to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            records = client.sync_by_date_range(from_date, to_date)
        elif specific_date:
            if isinstance(specific_date, str):
                specific_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
            records = client.fetch_by_date(specific_date)
        else:
            records = client.sync_all(days_back=days_back)

        records = client._filter_records(records, exclude_one_prefix=True)
        mapped = []
        for record in records:
            try:
                m = client._map_api_to_model(record)
                m['status'] = 'Delivered'
                mapped.append(m)
            except Exception as e:
                logger.error(f"Error mapping record {record.get('DocNum', 'unknown')}: {e}")

        if not mapped:
            logger.info("No records to save")
            return {'stats': {'created': 0, 'updated': 0, 'errors': 0, 'items_created': 0, 'items_updated': 0}, 'duration': 0}

        stats = save_delivery_order_records(mapped, {})
        duration = (datetime.now() - start).total_seconds()
        logger.info(f"sync_non_one_delivery_orders_core completed: created={stats['created']}, updated={stats['updated']}, "
                   f"duration={duration:.2f}s")
        return {'stats': stats, 'duration': duration, 'records_fetched': len(records)}
    except Exception as e:
        logger.error(f"sync_non_one_delivery_orders_core failed: {e}", exc_info=True)
        raise


def sync_invoices_core(days_back=3, specific_date=None, from_date=None, to_date=None):
    """Sync invoice numbers from DO Invoice API to local DB."""
    logger = _get_entity_logger('invoices')
    start = datetime.now()
    today = date.today()

    if from_date and to_date:
        if isinstance(from_date, str):
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        if isinstance(to_date, str):
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    elif specific_date:
        if isinstance(specific_date, str):
            specific_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
        from_date = specific_date
        to_date = specific_date
    else:
        to_date = today
        from_date = today - timedelta(days=days_back - 1)

    logger.info(f"Starting sync_invoices_core: from={from_date}, to={to_date}")

    try:
        client = SAPAPIClient()
        invoice_records = client.fetch_do_invoices(from_date, to_date)

        if not invoice_records:
            logger.info("No invoice records fetched")
            return {'stats': {'updated': 0, 'not_found': 0, 'errors': 0, 'duplicates_resolved': 0, 'credit_payments_deleted': 0}, 'duration': 0}

        do_invoice_map = {}
        for record in invoice_records:
            do_number = str(record.get('DO', '')).strip()
            if not do_number:
                continue
            invoice_value = record.get('INVOICE')
            amount_value = record.get('AMOUNT')
            amount = None
            if amount_value is not None:
                try:
                    amount = Decimal(str(amount_value))
                except (InvalidOperation, ValueError, TypeError):
                    pass
            if do_number not in do_invoice_map:
                do_invoice_map[do_number] = {'invoice': invoice_value, 'amount': amount}
            elif do_invoice_map[do_number]['amount'] is None and amount is not None:
                do_invoice_map[do_number]['amount'] = amount

        stats = {'updated': 0, 'not_found': 0, 'duplicates_resolved': 0, 'credit_payments_deleted': 0, 'errors': 0}
        errors = []

        for do_number, invoice_data in do_invoice_map.items():
            try:
                base_invoice = _normalize_invoice(invoice_data['invoice'])
                try:
                    order = DeliveryOrder.objects.get(do_number=do_number)
                    old_invoice = order.invoice_number
                    final_invoice = _make_invoice_unique(base_invoice, order)
                    if final_invoice != base_invoice:
                        stats['duplicates_resolved'] += 1
                    if old_invoice and old_invoice != final_invoice:
                        deleted_count = CreditPayment.objects.filter(delivery_order=order).delete()[0]
                        if deleted_count > 0:
                            stats['credit_payments_deleted'] += deleted_count
                    order.invoice_number = final_invoice
                    if invoice_data['amount'] is not None:
                        order.amount = invoice_data['amount']
                    order.save()
                    stats['updated'] += 1
                except DeliveryOrder.DoesNotExist:
                    stats['not_found'] += 1
            except Exception as e:
                stats['errors'] += 1
                errors.append(f"DO {do_number}: {e}")
                logger.error(f"Error processing DO {do_number}: {e}", exc_info=True)

        duration = (datetime.now() - start).total_seconds()
        logger.info(f"sync_invoices_core completed: updated={stats['updated']}, not_found={stats['not_found']}, "
                   f"duplicates_resolved={stats['duplicates_resolved']}, credit_payments_deleted={stats['credit_payments_deleted']}, "
                   f"errors={stats['errors']}, duration={duration:.2f}s")
        return {'stats': stats, 'duration': duration, 'records_fetched': len(invoice_records)}
    except Exception as e:
        logger.error(f"sync_invoices_core failed: {e}", exc_info=True)
        raise


def sync_cancelled_orders_core(last_pages=5):
    """Fetch cancelled orders from API and update local DB status to Cancelled."""
    logger = _get_entity_logger('cancelled')
    start = datetime.now()
    logger.info("Starting sync_cancelled_orders_core")

    try:
        client = SAPAPIClient()
        all_cancelled = []
        seen_docnums = set()
        per_page = 20

        for cancel_status in ["csCancellation", "csYes"]:
            payload = {"CancelStatus": cancel_status}
            first_page = client._make_request(payload, page_number=1)
            records = first_page.get('value', [])
            total_count = first_page.get('count', len(records))
            total_pages = (total_count + per_page - 1) // per_page
            if total_pages == 0:
                continue
            start_page = max(1, total_pages - last_pages + 1)
            for page in range(start_page, total_pages + 1):
                page_result = client._make_request(payload, page_number=page)
                page_records = page_result.get('value', [])
                for record in page_records:
                    docnum = str(record.get('DocNum', ''))
                    if docnum and docnum not in seen_docnums:
                        seen_docnums.add(docnum)
                        all_cancelled.append(record)

        cancelled_docnums = []
        for record in all_cancelled:
            docnum = str(record.get('DocNum', '')).strip()
            if docnum:
                try:
                    if int(docnum) > 126000000:
                        cancelled_docnums.append(docnum)
                except ValueError:
                    pass

        if not cancelled_docnums:
            logger.info("No cancelled orders with do_number > 126000000")
            return {'stats': {'updated': 0}, 'duration': 0}

        records = [{'do_number': d, 'status': 'Cancelled'} for d in cancelled_docnums]
        stats = save_delivery_order_records(records, {})
        duration = (datetime.now() - start).total_seconds()
        logger.info(f"sync_cancelled_orders_core completed: updated={stats['updated']}, duration={duration:.2f}s")
        return {'stats': stats, 'duration': duration, 'cancelled_count': len(cancelled_docnums)}
    except Exception as e:
        logger.error(f"sync_cancelled_orders_core failed: {e}", exc_info=True)
        raise


def sync_all_core(days_back=3):
    """Sync delivery orders + non-one orders + invoices (one cron covers all)."""
    logger = _get_entity_logger('orders')
    start = datetime.now()
    logger.info(f"Starting sync_all_core: days_back={days_back}")

    result_do = sync_delivery_orders_core(days_back=days_back)
    result_non_one = sync_non_one_delivery_orders_core(days_back=days_back)
    result_inv = sync_invoices_core(days_back=days_back)

    duration = (datetime.now() - start).total_seconds()
    logger.info(f"sync_all_core completed: duration={duration:.2f}s")
    return {
        'delivery_orders': result_do,
        'non_one': result_non_one,
        'invoices': result_inv,
        'duration': duration
    }
