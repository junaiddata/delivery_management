"""
VPS management command: sync delivery orders NOT starting with "1" from API to local DB.
Logs to logs/sync_non_one.log.
"""
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from orders.sync_services import sync_non_one_delivery_orders_core, _get_entity_logger


class Command(BaseCommand):
    help = 'VPS: Sync non-one delivery orders from API to local database'

    def add_arguments(self, parser):
        parser.add_argument('--days-back', type=int, default=getattr(settings, 'SYNC_DAYS_BACK', 3))
        parser.add_argument('--date', type=str, help='Sync specific date (YYYY-MM-DD)')
        parser.add_argument('--from-date', type=str, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--to-date', type=str, help='End date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        logger = _get_entity_logger('non_one')
        logger.info(f"sync_non_one_orders_vps started: days_back={options['days_back']}, "
                    f"date={options.get('date')}, from={options.get('from_date')}, to={options.get('to_date')}")

        try:
            result = sync_non_one_delivery_orders_core(
                days_back=options['days_back'],
                specific_date=options.get('date'),
                from_date=options.get('from_date'),
                to_date=options.get('to_date'),
                docnum=None
            )
            stats = result.get('stats', {})
            duration = result.get('duration', 0)
            logger.info(
                f"sync_non_one_orders_vps completed: created={stats.get('created', 0)}, "
                f"updated={stats.get('updated', 0)}, duration={duration:.2f}s"
            )
            self.stdout.write(self.style.SUCCESS(
                f"[OK] Sync completed: created={stats.get('created', 0)}, "
                f"updated={stats.get('updated', 0)}, duration={duration:.2f}s"
            ))
        except Exception as e:
            logger.error(f"sync_non_one_orders_vps failed: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"[ERROR] {e}"))
            raise
