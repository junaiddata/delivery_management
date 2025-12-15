import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from orders.models import DeliveryOrder


class Command(BaseCommand):
    help = "Fix customer_code, customer_name, and LPO for DOs dated 13-12-2025"

    def handle(self, *args, **options):
        import csv
        from datetime import datetime
        from orders.models import DeliveryOrder

        FILE_PATH = "do_fix_13_12_2025.csv"
        TARGET_DATE = datetime.strptime("13/12/2025", "%d/%m/%Y").date()

        updated = 0
        skipped = 0
        not_found = 0

        with open(FILE_PATH, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row in reader:
                # ✅ Handle BOM + empty rows
                do_number = (
                    row.get("DO")
                    or row.get("\ufeffDO")
                    or ""
                ).strip()

                if not do_number:
                    skipped += 1
                    continue

                customer_code = (row.get("CUSTOMER CODE") or "").strip() or None
                customer_name = (row.get("CUSTOMER") or "").strip() or None
                lpo = (row.get("LPO") or "").strip() or None

                try:
                    do = DeliveryOrder.objects.get(
                        do_number=do_number,
                        date=TARGET_DATE
                    )

                    do.customer_code = customer_code
                    do.customer_name = customer_name
                    do.lpo = lpo

                    do.save(update_fields=[
                        "customer_code",
                        "customer_name",
                        "lpo"
                    ])

                    updated += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Updated DO {do_number}"
                    ))

                except DeliveryOrder.DoesNotExist:
                    not_found += 1
                    self.stdout.write(self.style.WARNING(
                        f"DO not found: {do_number}"
                    ))

        self.stdout.write("\n========= SUMMARY =========")
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated}"))
        self.stdout.write(self.style.WARNING(f"Skipped empty rows: {skipped}"))
        self.stdout.write(self.style.WARNING(f"Not found: {not_found}"))