import os
import pandas as pd
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from orders.models import DeliveryOrder, MessageStatus


class Command(BaseCommand):
    help = 'Generate daily delivery and message status report (Excel)'

    def handle(self, *args, **options):
        """
        Generate Excel report of:
        - DeliveryOrder with status "Out for Delivery" from today
        - Cross-matched with MessageStatus records sent today
        """
        try:
            # Get today's date
            today = timezone.now().date()

            # Query DeliveryOrder with status "Out for Delivery" from today
            delivery_orders = DeliveryOrder.objects.filter(
                status='Out for Delivery',
                date=today
            ).select_related('customer').order_by('do_number')

            self.stdout.write(
                self.style.SUCCESS(f'Found {delivery_orders.count()} delivery orders with status "Out for Delivery"')
            )

            # Query MessageStatus records from today
            today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
            today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
            
            message_statuses = MessageStatus.objects.all()
            # Parse timestamp and filter (timestamp is stored as string)
            today_messages = {}
            for msg in message_statuses:
                try:
                    # Try to parse timestamp - adjust format based on your data
                    msg_date = datetime.fromisoformat(msg.timestamp.replace('Z', '+00:00')).date()
                    if msg_date == today:
                        today_messages[msg.recipient_id] = msg
                except:
                    pass

            self.stdout.write(
                self.style.SUCCESS(f'Found {len(today_messages)} message statuses from today')
            )

            # Build report data by cross-matching
            report_data = []
            for do in delivery_orders:
                mobile = do.mobile_number or ''
                recipient_id = mobile.lstrip('+')  # Remove + prefix for matching
                
                # Check if message was sent
                message_status = today_messages.get(recipient_id)
                
                if message_status:
                    status_display = f"✓ {message_status.status.title()}"
                    message_id = message_status.message_id
                else:
                    status_display = "✗ Not Sent"
                    message_id = "N/A"

                report_data.append({
                    'DO Number': do.do_number,
                    'Customer Name': do.customer_name,
                    'Customer Code': do.customer_code,
                    'Salesman': do.salesman or 'N/A',
                    'Mobile Number': mobile,
                    'City': do.city or 'N/A',
                    'Area': do.area or 'N/A',
                    'Driver': do.driver or 'N/A',
                    'Message Status': status_display,
                    'Message ID': message_id,
                    'Amount': do.amount or 0,
                    'DO Date': do.date,
                })

            # Create DataFrame
            df = pd.DataFrame(report_data)

            # Ensure reports folder exists
            reports_folder = getattr(settings, 'DAILY_REPORTS_FOLDER', 'delivery_management/reports')
            os.makedirs(reports_folder, exist_ok=True)

            # Generate filename with date
            filename = f'delivery_report_{today.strftime("%Y-%m-%d")}.xlsx'
            filepath = os.path.join(reports_folder, filename)

            # Write to Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Delivery Report')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Delivery Report']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            self.stdout.write(
                self.style.SUCCESS(f'Report generated successfully: {filepath}')
            )

            # Print summary
            if len(df) > 0:
                sent_count = df['Message Status'].str.contains('✓', na=False).sum()
                failed_count = df['Message Status'].str.contains('✗', na=False).sum()
            else:
                sent_count = 0
                failed_count = 0

            self.stdout.write(self.style.SUCCESS(f'\n📊 Report Summary:'))
            self.stdout.write(self.style.SUCCESS(f'   Total Orders Out for Delivery: {len(df)}'))
            self.stdout.write(self.style.SUCCESS(f'   ✓ Messages Sent: {sent_count}'))
            self.stdout.write(self.style.SUCCESS(f'   ✗ Messages Failed/Not Sent: {failed_count}'))
            self.stdout.write(self.style.SUCCESS(f'   📁 Saved to: {filepath}'))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error generating report: {str(e)}')
            )
            raise
