import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from orders.models import DeliveryOrder


class Command(BaseCommand):
    help = "Fix customer_code, customer_name, and LPO for DOs dated 13-12-2025"

    def handle(self, *args, **options):
        FILE_PATH = "do_fix_13_12_2025.csv"
        TARGET_DATE = datetime.strptime("13/12/2025", "%d/%m/%Y").date()

        updated = 0
        not_found = 0

        try:
            with open(FILE_PATH, newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for row in reader:
                    do_number = str(row.get("DO", "")).strip()

                    customer_name = row.get("CUSTOMER")
                    customer_code = row.get("CUSTOMER CODE")
                    lpo = row.get("LPO")

                    customer_name = customer_name.strip() if customer_name else None
                    customer_code = customer_code.strip() if customer_code else None
                    lpo = lpo.strip() if lpo else None

                    try:
                        do = DeliveryOrder.objects.get(
                            do_number=do_number,
                            date=TARGET_DATE
                        )

                        do.customer_name = customer_name
                        do.customer_code = customer_code
                        do.lpo = lpo

                        # 🔒 update only these fields
                        do.save(update_fields=[
                            "customer_name",
                            "customer_code",
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

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                f"CSV file not found: {FILE_PATH}"
            ))
            return

        self.stdout.write("\n========== SUMMARY ==========")
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated} DOs"))
        self.stdout.write(self.style.WARNING(f"Not found: {not_found} DOs"))
