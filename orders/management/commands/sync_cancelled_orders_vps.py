"""
VPS management command: sync cancelled order status from API to local DB.
Logs to logs/sync_cancelled.log.
"""
from django.core.management.base import BaseCommand
from orders.sync_services import sync_cancelled_orders_core, _get_entity_logger


class Command(BaseCommand):
    help = 'VPS: Sync cancelled delivery order status to local database'

    def handle(self, *args, **options):
        logger = _get_entity_logger('cancelled')
        logger.info("sync_cancelled_orders_vps started")

        try:
            result = sync_cancelled_orders_core()
            stats = result.get('stats', {})
            duration = result.get('duration', 0)
            logger.info(
                f"sync_cancelled_orders_vps completed: updated={stats.get('updated', 0)}, "
                f"duration={duration:.2f}s"
            )
            self.stdout.write(self.style.SUCCESS(
                f"[OK] Sync completed: updated={stats.get('updated', 0)}, duration={duration:.2f}s"
            ))
        except Exception as e:
            logger.error(f"sync_cancelled_orders_vps failed: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"[ERROR] {e}"))
            raise
