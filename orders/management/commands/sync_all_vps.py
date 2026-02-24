"""
VPS management command: sync delivery orders + non-one orders + invoices (one cron covers all).
Logs to logs/sync_orders.log.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from orders.sync_services import sync_all_core, _get_entity_logger


class Command(BaseCommand):
    help = 'VPS: Sync delivery orders + non-one orders + invoices (sync all)'

    def add_arguments(self, parser):
        parser.add_argument('--days-back', type=int, default=getattr(settings, 'SYNC_DAYS_BACK', 3))

    def handle(self, *args, **options):
        logger = _get_entity_logger('orders')
        logger.info(f"sync_all_vps started: days_back={options['days_back']}")

        try:
            result = sync_all_core(days_back=options['days_back'])
            do_stats = result.get('delivery_orders', {}).get('stats', {})
            non_one_stats = result.get('non_one', {}).get('stats', {})
            inv_stats = result.get('invoices', {}).get('stats', {})
            duration = result.get('duration', 0)
            logger.info(
                f"sync_all_vps completed: DO created={do_stats.get('created', 0)}, "
                f"updated={do_stats.get('updated', 0)}, "
                f"Non-one created={non_one_stats.get('created', 0)}, updated={non_one_stats.get('updated', 0)}, "
                f"Invoices updated={inv_stats.get('updated', 0)}, duration={duration:.2f}s"
            )
            self.stdout.write(self.style.SUCCESS(
                f"[OK] Sync all completed: DO created={do_stats.get('created', 0)}, "
                f"updated={do_stats.get('updated', 0)}; "
                f"Non-one created={non_one_stats.get('created', 0)}, updated={non_one_stats.get('updated', 0)}; "
                f"Invoices updated={inv_stats.get('updated', 0)}, duration={duration:.2f}s"
            ))
        except Exception as e:
            logger.error(f"sync_all_vps failed: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"[ERROR] {e}"))
            raise
