# Delivery & Finance Management System

## Project Handbook and Presentation Deck

**Purpose:** A complete user-friendly explanation of what the app does, who uses it, and how each business process works.

**Audience:** Management, warehouse, security, sales, drivers, accounts, collection team, and non-technical users.

---

# What This App Is

The Delivery & Finance Management System is a web application for controlling the full delivery order lifecycle.

It brings delivery orders, vehicles, drivers, invoice tracking, customer credit follow-up, payment collection, SAP invoice analysis, and sync operations into one shared system.

The app is designed so each department sees the work relevant to them and updates the same central delivery record.

---

# Main Problems It Solves

- Delivery orders are no longer managed only through Excel sheets or manual follow-up.
- Warehouse can assign vehicles and drivers from one screen.
- Security can verify which vehicle is leaving or entering.
- Drivers can update delivery status.
- Salesmen can check their own customer deliveries.
- Accounts can mark delivered orders as received by accounts.
- Collection and managers can track payment due dates and approval requests.
- Admin can sync delivery and invoice data from SAP/API instead of entering everything manually.

---

# High-Level App Flow

1. Delivery orders enter the app through SAP/API sync or Excel upload.
2. Admin or warehouse reviews pending delivery orders.
3. Warehouse assigns vehicle, driver, and delivery status.
4. Security verifies the vehicle and delivery order movement.
5. Driver updates delivery progress.
6. Delivered orders move to accounts.
7. Accounts marks documents as received.
8. Collection follows payment and credit status.
9. Managers review pending approvals and finance dashboards.
10. Admin monitors sync, reports, and master data.

---

# Main User Roles

The app uses role-based access. Each user role gets a different starting point and different permissions.

- **Admin / Junaid Admin:** Overall control, orders, sync settings, exports, edits.
- **Warehouse:** Vehicle assignment, DO loading, delivery preparation.
- **Security:** Vehicle verification and gate-level delivery control.
- **Driver:** Assigned vehicle and delivery status update.
- **Salesman:** Own delivery orders and item details.
- **Accounts:** Delivered orders, received documents, account handover.
- **Collection:** Customer credit and payment follow-up.
- **Manager:** Approval requests, finance overview, credit dashboard.

---

# Home Dashboard

After login, the home screen identifies the user and sends them to the correct working area.

Examples:

- Admin sees order management, store DOs, and sync settings.
- Warehouse sees vehicle list.
- Security sees security dashboard.
- Salesman sees personal order list.
- Driver sees driver dashboard.
- Accounts sees accounting portal.
- Manager sees finance overview.
- Collection sees customer database.

This prevents users from opening screens that are not part of their job.

---

# Core Business Records

The app stores and connects these main records:

- **Customer:** Customer code, name, credit limit, balance, phone number, payment terms.
- **Delivery Order:** DO number, invoice, customer, date, city, area, salesman, amount, vehicle, driver, status.
- **Delivery Items:** Item code, item description, quantity, price for each DO.
- **Vehicle:** Vehicle number used for delivery assignment.
- **Transfer Order:** Store or transfer movement records.
- **Credit Payment:** Due date, exceeded days, cheque date, approval status, payment received.
- **SAP Invoice/Credit Data:** Uploaded or synced sales, credit note, GP, and item-level data.

---

# Delivery Order Statuses

Delivery orders move through clear statuses:

- **Pending:** Order exists but delivery action is not completed.
- **Loaded:** Warehouse has prepared or loaded the order.
- **Out for Delivery:** Vehicle/driver is moving with the order.
- **Delivered:** Delivery completed.
- **Partial Delivery:** Some items delivered, not full completion.
- **Not Delivered:** Delivery attempt failed.
- **Cancelled:** Order cancelled.
- **Received by A/c:** Accounts has received the delivered order documents.
- **GRV:** Goods return related status.
- **On Hold:** Order temporarily stopped.

---

# Admin Order Management

Admin users can view and manage all delivery orders.

The Delivery Orders page shows:

- Total order count.
- Counts by status such as Pending, Out for Delivery, On Hold, Delivered.
- Filters by search, date, customer, salesman, city, area, vehicle, driver, and status.
- Main order details including DO number, invoice, customer, mobile, amount, vehicle, driver, and remarks.
- Edit option for invoice number, credit note, amount, mobile number, vehicle, driver, status, and remark.

---

# Admin Editing Workflow

When an admin edits an order:

1. Admin opens the Delivery Orders page.
2. Admin searches or filters for the required DO.
3. Admin clicks Edit.
4. The app opens the order edit form.
5. Admin updates invoice, amount, credit note, mobile, vehicle, driver, status, or remark.
6. Admin saves.
7. The order list reloads with the updated information.

This is useful when invoice numbers arrive later, mobile numbers need correction, or operational status changes.

---

# Warehouse Workflow

Warehouse users work mainly from vehicle and pending DO screens.

The warehouse process is:

1. Review pending delivery orders.
2. Decide which vehicle will carry the orders.
3. Assign vehicle and driver.
4. Mark orders as loaded or out for delivery.
5. Handle special cases such as hold, GRV, rental vehicle, salesman delivery, customer pickup, partial delivery, or cancellation.
6. Keep the delivery status updated so other departments can see progress.

Warehouse is the operational control point before delivery leaves.

---

# Vehicle-Based Delivery Control

The app groups many delivery actions around vehicles.

Vehicle screens help users answer:

- Which vehicle has which orders?
- Which driver is assigned?
- Which DOs are loaded?
- Which DOs are out for delivery?
- Which vehicle needs security verification?
- Which deliveries are completed or pending?

This gives warehouse, security, and drivers one shared view of movement.

---

# Security Workflow

Security users verify vehicle movement.

The security process is:

1. Open Security Dashboard.
2. View vehicles requiring security action.
3. Select a vehicle.
4. Verify the linked delivery orders.
5. Update security status when the vehicle is approved for movement.
6. The operational record is updated for warehouse/admin visibility.

Security acts as a checkpoint between warehouse preparation and actual vehicle movement.

---

# Driver Workflow

Drivers use the driver dashboard to work on assigned vehicle deliveries.

The driver process is:

1. Login as Driver.
2. Open Driver Dashboard.
3. View assigned vehicle and delivery orders.
4. Update delivery order status after delivery attempt.
5. Mark orders as Delivered, Partial Delivery, Not Delivered, or another allowed delivery status.
6. The status becomes visible to warehouse, admin, sales, and accounts.

The driver does not need to understand the full back-office system.

---

# Salesman Workflow

Salesmen can view their own delivery orders.

The salesman process is:

1. Login as Salesman.
2. Open My Orders.
3. Review customer delivery orders linked to the salesman.
4. Search or filter order information.
5. Open DO item details when needed.
6. Export or review customer delivery information.

This helps salesmen answer customer questions about delivery status, item details, and pending deliveries.

---

# DO Item Details

Each delivery order can have item-level details.

The item screen shows:

- DO number.
- Item code.
- Item description.
- Quantity.
- Price.

This is useful when a customer or salesman asks what exactly was included in a delivery order.

---

# Accounts Workflow

Accounts handles delivered orders after the delivery team finishes.

The accounts process is:

1. Open Accounting Portal.
2. View delivered orders.
3. Filter and search delivered records.
4. Check invoice and delivery information.
5. Mark the order as received by accounts.
6. Move completed records to the received list.
7. Export delivered/received data when required.

This creates a clean handover from operations to accounting.

---

# Received by Accounts

The status **Received by A/c** means accounts has received the delivery order documentation.

This status is important because:

- Delivery team knows the documents reached accounts.
- Accounts can begin or continue invoice/payment follow-up.
- Management can separate physically delivered orders from accounts-received orders.
- Pending document handover becomes easier to track.

---

# Transfer Orders

The system also supports transfer orders.

Transfer order screens allow users to:

- Upload transfer data.
- View transfer list.
- Assign vehicles to transfer movement.
- Update transfer vehicle information.
- Mark transfer status as Pending or Delivered.

This is separate from normal customer delivery orders but uses a similar operational flow.

---

# Customer and Credit Management

The finance side tracks customers and credit follow-up.

Customer records include:

- Customer code.
- Customer name.
- Credit limit days.
- Credit limit amount.
- Additional terms.
- Opening balance.
- Mobile number.
- Purchase frequency information.

Collection and sales users use this area to monitor customer payment behavior and credit-related actions.

---

# Credit Payment Tracking

Credit payment records connect invoices to due dates and collection status.

The system tracks:

- Invoice number.
- Linked delivery order.
- Due date.
- Days exceeded.
- Approval status: Pending, Approved, Declined.
- Customer cheque date.
- Payment received yes/no.
- Remarks.

This makes overdue follow-up visible instead of hidden in separate files.

---

# Collection Workflow

Collection users work with customer payment and credit entries.

The collection process is:

1. Open Customer Database.
2. Select a customer.
3. Review delivery/invoice credit entries.
4. Update cheque date if available.
5. Mark payment received when collected.
6. Submit entries to MD/Manager when approval is needed.
7. Use combined and bulk actions for multiple entries.

This supports daily collection follow-up and escalation.

---

# Manager / MD Approval Workflow

Managers review requests that require approval.

The approval process is:

1. Collection or salesman submits a request.
2. Request appears in MD pending requests.
3. Manager reviews customer, invoice, due date, amount, and remarks.
4. Manager approves or declines the request.
5. Status updates in the customer credit/payment record.
6. Collection team can continue follow-up based on the decision.

The app supports both single-entry and bulk approval requests.

---

# Credit Dashboard

The credit dashboard gives a finance overview of payment records.

It shows:

- Total DO amount.
- Total delivered amount.
- Total credit note.
- Effective outstanding.
- Payment records by customer, invoice, due date, payment status, and exceeded days.
- Filters by search, date range, payment received, approval status, and customer.
- Export options for reporting.

This dashboard helps managers quickly identify pending and overdue exposure.

---

# Customer Frequency Analysis

The app includes customer purchase frequency analysis.

It helps identify:

- One-month customers.
- Two-month customers.
- All-month customers.
- Number of invoices.
- Months bought.
- Total value.
- Gross profit and GP percentage for admin users.

Users can filter by group, month range, salesman, and customer name.

This is useful for sales performance review and customer retention follow-up.

---

# SAP Invoice and Credit Note Handling

The system stores SAP invoice and credit note data for reporting.

It can track:

- Invoice upload batches.
- Invoice number, date, customer, salesman, and document total.
- Credit note upload batches.
- Credit note number, date, customer, salesman, and credit amount.
- GP lines by date, customer, salesman, and item.
- Item-level sales facts including quantity, net sales, and gross profit.

This makes SAP data searchable and usable inside the app.

---

# SAP Upload Workflow

For SAP analysis pages, users upload Excel files containing invoice or credit data.

The upload process is:

1. User opens the SAP upload page.
2. User selects the Excel file.
3. App reads rows from the file.
4. App stores the upload as a batch for traceability.
5. Invoice, credit note, GP, and item records are saved.
6. Analysis pages use the latest stored data.

The batch history helps identify which upload created the data.

---

# Sync Settings

Admin users can sync data from the SAP/API source into the local app database.

The Sync Settings page supports:

- **Sync all:** Delivery orders, non-one orders, and invoices together.
- **Sync cancelled orders:** Update cancelled order statuses.
- **Delivery orders:** DOs starting with `1`.
- **Non-one orders:** DOs not starting with `1`.
- **Invoices:** Invoice numbers and invoice amounts.
- Date controls: last N days, specific date, or date range where supported.

Logs are written to `logs/sync_*.log`.

---

# Automatic Sync Architecture

The system can run sync automatically on a VPS/server.

Typical setup:

1. A secure tunnel connects the server to the internal SAP/API source.
2. The server calls the API through the tunnel.
3. Scheduled commands run every few minutes or daily.
4. Delivery orders, non-one orders, invoices, and cancelled orders are updated.
5. Logs are saved for troubleshooting.

This reduces manual work and keeps the app current.

---

# What Happens During Delivery Order Sync

When delivery orders sync:

1. The app asks the SAP/API for recent delivery orders.
2. It filters normal delivery orders that start with `1`.
3. It maps SAP fields into app fields such as DO number, customer, city, area, salesman, amount, and mobile number.
4. It creates new orders if they do not exist.
5. It updates existing orders if they already exist.
6. It saves item lines for each delivery order.
7. It logs created, updated, item-created, item-updated, and error counts.

---

# What Happens During Invoice Sync

Invoice sync updates delivery orders with invoice information.

Process:

1. App calls the DO Invoice API for a date range.
2. It matches invoice records to existing DO numbers.
3. It updates invoice number and amount on each matched delivery order.
4. If invoice number is blank or invalid, the app creates a safe placeholder.
5. If duplicate invoice numbers appear, the app adds suffixes to keep them unique.
6. If invoice number changes, linked credit payment records may be refreshed.

---

# Cancelled Order Sync

Cancelled order sync checks SAP/API cancellation statuses.

Process:

1. App fetches records marked cancelled.
2. It checks recent pages from the API.
3. It keeps valid DO numbers only.
4. It updates matching local delivery orders to **Cancelled**.
5. It logs how many records were updated.

This keeps cancelled SAP orders from appearing as active delivery work.

---

# WhatsApp and Message Tracking

The app includes message-related records and webhook handling.

It can store:

- Customer replies.
- Sender number.
- Message body.
- Received time.
- Message delivery status such as sent, delivered, or read.

This supports customer communication tracking around delivery messages.

---

# Reports and Exports

The app supports exports for operational and finance use.

Examples:

- Delivery orders to Excel.
- Delivery orders to PDF.
- Salesman orders to PDF.
- Accounts delivered orders to Excel.
- Customer frequency data to CSV.
- Credit dashboard exports.
- Daily delivery report command.

Exports help teams share information outside the web app when needed.

---

# Search and Filtering

Most major screens support filtering so users do not need to scroll through all records.

Common filters include:

- DO number.
- Invoice number.
- Customer name.
- Customer code.
- Date range.
- Salesman.
- City.
- Area.
- Vehicle.
- Driver.
- Status.
- Payment received.
- Approval status.

This makes the app practical for high-volume daily operations.

---

# Data Quality Rules

The system applies several practical data rules:

- DO number is unique.
- Invoice number is unique when available.
- Customer is linked by customer code where possible.
- New customer records can be created automatically when a DO has a new customer code.
- Mobile numbers are normalized into UAE format where possible.
- SAP salesman names are mapped to cleaner internal names.
- Item lines are updated instead of duplicated when the same DO and item already exist.

---

# User Access Summary

| Role | Main Screens | Main Responsibilities |
|---|---|---|
| Admin | Orders, Store DOs, Sync Settings | Full control, edits, sync, reporting |
| Warehouse | Vehicle List, Pending DOs | Assign vehicles/drivers, load orders |
| Security | Security Dashboard | Verify vehicle movement |
| Driver | Driver Dashboard | Update delivery status |
| Salesman | My Orders, DO Items | Track own customer deliveries |
| Accounts | Delivered/Received Orders | Mark received by accounts |
| Collection | Customers, Credit Entries | Follow payments and cheque dates |
| Manager | MD Dashboard, Pending Requests | Approve/decline finance requests |

---

# Example End-to-End Delivery Scenario

1. SAP creates a delivery order.
2. Sync brings the DO into the app.
3. Admin or warehouse sees it as Pending.
4. Warehouse assigns vehicle and driver.
5. Warehouse marks it Loaded or Out for Delivery.
6. Security verifies the vehicle.
7. Driver completes delivery and updates status.
8. Salesman can check the delivery status.
9. Accounts marks delivered documents as received.
10. Collection tracks payment if the customer is on credit.
11. Manager reviews any approval request if payment is delayed or needs special approval.

---

# Example Finance Scenario

1. Invoice data is synced or uploaded from SAP.
2. Delivery order receives invoice number and amount.
3. Credit payment record tracks due date.
4. Collection sees overdue or upcoming payment entries.
5. Customer cheque date is entered when available.
6. Payment is marked received after collection.
7. Requests needing management approval are submitted.
8. Manager approves or declines.
9. Dashboard updates totals and outstanding position.

---

# Daily Operating Routine

Recommended daily use:

- Admin checks sync status and failed sync logs.
- Warehouse checks pending orders and vehicle assignment.
- Security verifies vehicle movement.
- Drivers update delivery outcomes.
- Salesmen check customer delivery queries.
- Accounts clears delivered documents into received records.
- Collection follows due and overdue customers.
- Manager checks pending approval requests and credit dashboard.

---

# Troubleshooting for Users

If data is missing:

- Check whether the sync ran successfully.
- Confirm the correct date range was used.
- Search by DO number instead of customer name.
- Check whether it is a normal DO or non-one/store DO.
- Ask admin to verify logs in `logs/sync_*.log`.

If sync fails:

- Confirm the SAP/API connection or tunnel is running.
- Try Sync Settings ping page.
- Check server timeout if the sync takes a long time.
- Review sync log files.

---

# Benefits for Management

- One shared source for delivery and finance status.
- Better visibility of pending, loaded, delivered, cancelled, and accounts-received orders.
- Easier overdue payment tracking.
- Clear role ownership across departments.
- Faster customer response from sales and accounts.
- Reduced dependency on manual Excel-only workflows.
- Better reporting through exports and dashboards.

---

# Benefits for Operations

- Warehouse can manage vehicle assignment from one place.
- Drivers can update delivery outcomes directly.
- Security has a clear verification screen.
- Admin can fix order details without database work.
- Status badges and filters show workload quickly.
- Remarks allow context to stay attached to each order.

---

# Benefits for Finance and Collection

- Invoice, DO, and customer information are connected.
- Due dates and exceeded days are visible.
- Payment received status is tracked.
- Customer credit limits and terms are available.
- Credit notes and effective outstanding can be reviewed.
- Manager approvals are structured instead of informal.
- SAP invoice and GP data supports customer frequency analysis.

---

# What a Non-Technical User Should Remember

The app is not just a list of orders.

It is a workflow system:

- SAP/API brings orders and invoices in.
- Operations updates delivery progress.
- Security verifies movement.
- Drivers update completion.
- Accounts confirms document handover.
- Collection follows payments.
- Managers approve exceptions.
- Reports and dashboards show the current business position.

---

# Final Summary

The Delivery & Finance Management System connects delivery operations and finance follow-up in one web app.

It helps every department update the same record at the right stage, from SAP order creation to vehicle movement, delivery completion, accounts receipt, payment tracking, and management approval.

The result is better control, clearer responsibility, faster reporting, and less manual coordination across teams.

