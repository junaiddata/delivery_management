"""
VPS management command: sync invoice numbers from DO Invoice API to local DB.
Logs to logs/sync_invoices.log.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from orders.sync_services import sync_invoices_core, _get_entity_logger


class Command(BaseCommand):
    help = 'VPS: Sync invoice numbers from DO Invoice API to local database'

    def add_arguments(self, parser):
        parser.add_argument('--days-back', type=int, default=getattr(settings, 'SYNC_DAYS_BACK', 3))
        parser.add_argument('--date', type=str, help='Sync specific date (YYYY-MM-DD)')
        parser.add_argument('--from-date', type=str, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--to-date', type=str, help='End date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        logger = _get_entity_logger('invoices')
        logger.info(f"sync_invoices_vps started: days_back={options['days_back']}, "
                    f"date={options.get('date')}, from={options.get('from_date')}, to={options.get('to_date')}")

        try:
            result = sync_invoices_core(
                days_back=options['days_back'],
                specific_date=options.get('date'),
                from_date=options.get('from_date'),
                to_date=options.get('to_date')
            )
            stats = result.get('stats', {})
            duration = result.get('duration', 0)
            logger.info(
                f"sync_invoices_vps completed: updated={stats.get('updated', 0)}, "
                f"not_found={stats.get('not_found', 0)}, duration={duration:.2f}s"
            )
            self.stdout.write(self.style.SUCCESS(
                f"[OK] Sync completed: updated={stats.get('updated', 0)}, "
                f"not_found={stats.get('not_found', 0)}, duration={duration:.2f}s"
            ))
        except Exception as e:
            logger.error(f"sync_invoices_vps failed: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"[ERROR] {e}"))
            raise
