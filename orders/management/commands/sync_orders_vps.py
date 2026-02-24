"""
VPS management command: sync delivery orders (DOs starting with "1") from API to local DB.
Uses venv Python when run via crontab. Logs to logs/sync_orders.log.
"""
import logging
import logging.handlers
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from orders.sync_services import sync_delivery_orders_core, _get_entity_logger


class Command(BaseCommand):
    help = 'VPS: Sync delivery orders from API to local database (no HTTP push)'

    def add_arguments(self, parser):
        parser.add_argument('--days-back', type=int, default=getattr(settings, 'SYNC_DAYS_BACK', 3))
        parser.add_argument('--date', type=str, help='Sync specific date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        logger = _get_entity_logger('orders')
        logger.info(f"sync_orders_vps started: days_back={options['days_back']}, date={options.get('date')}")

        try:
            result = sync_delivery_orders_core(
                days_back=options['days_back'],
                specific_date=options.get('date'),
                docnum=None
            )
            stats = result.get('stats', {})
            duration = result.get('duration', 0)
            logger.info(
                f"sync_orders_vps completed: created={stats.get('created', 0)}, "
                f"updated={stats.get('updated', 0)}, duration={duration:.2f}s"
            )
            self.stdout.write(self.style.SUCCESS(
                f"[OK] Sync completed: created={stats.get('created', 0)}, "
                f"updated={stats.get('updated', 0)}, duration={duration:.2f}s"
            ))
        except Exception as e:
            logger.error(f"sync_orders_vps failed: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"[ERROR] {e}"))
            raise
