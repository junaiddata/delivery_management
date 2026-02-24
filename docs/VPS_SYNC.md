# VPS-centric Sync

All sync runs on the VPS. The PC only keeps the SSH reverse tunnel open.

## Architecture

- **Tunnel (run on PC):** `ssh -N -R 8443:<LOCAL_API_HOST>:<PORT> user@VPS_IP`
- On VPS, the app calls the API at `http://localhost:8443` (via tunnel).
- Sync is triggered by: (1) crontab on VPS, (2) manual buttons on the Settings page.

## Environment

Set on VPS:

```bash
export API_BASE_HOST=http://localhost:8443
```

Or in `.env`:

```
API_BASE_HOST=http://localhost:8443
```

On PC (local dev), the default `http://192.168.1.103` is used.

## Crontab

Use the project's venv Python. Example paths (adjust to your deployment):

```bash
# Sync all (delivery orders + non-one + invoices) - one cron covers all (every 5 minutes)
*/5 * * * * /var/www/delivery_management/venv/bin/python /var/www/delivery_management/manage.py sync_all_vps --days-back 3 >> /var/log/sync_all_cron.log 2>&1

# Cancelled orders (daily)
0 6 * * * /var/www/delivery_management/venv/bin/python /var/www/delivery_management/manage.py sync_cancelled_orders_vps >> /var/log/sync_cancelled_cron.log 2>&1
```

Optional individual crontabs (if you prefer separate schedules):

```bash
# Delivery orders only
*/5 * * * * /var/www/delivery_management/venv/bin/python /var/www/delivery_management/manage.py sync_orders_vps --days-back 3 >> /var/log/sync_orders_cron.log 2>&1
# Non-one orders only
0 * * * * /var/www/delivery_management/venv/bin/python /var/www/delivery_management/manage.py sync_non_one_orders_vps --days-back 3 >> /var/log/sync_non_one_cron.log 2>&1
# Invoices only
*/10 * * * * /var/www/delivery_management/venv/bin/python /var/www/delivery_management/manage.py sync_invoices_vps --days-back 3 >> /var/log/sync_invoices_cron.log 2>&1
```

**Note:** Cron's stdout/stderr (`/var/log/sync_*_cron.log`) are not rotated unless you add logrotate. The **application** logs in `logs/sync_*.log` (inside the project) use Python's RotatingFileHandler (10MB, 5 backups).

## Optional logrotate

To rotate cron output logs, add `/etc/logrotate.d/delivery-sync`:

```
/var/log/sync_*_cron.log {
    daily
    rotate 7
    missingok
    notifempty
}
```

## Deploying to VPS

1. **Deploy code** to the VPS.
2. **Run migrations:** `python manage.py migrate`
3. **Set env:** `API_BASE_HOST=http://localhost:8443` (in `.env` or export).
4. **On PC:** Start tunnel: `ssh -N -R 8443:<LOCAL_API_HOST>:<PORT> user@VPS_IP`
   - Replace `<LOCAL_API_HOST>` with the IP/host where the SAP API runs (e.g. `192.168.1.103`).
   - Replace `<PORT>` with the API port (e.g. `80`).
5. **Verify crontab:** Ensure entries use the venv Python path.
6. **Test manual sync:** Go to Settings > Sync Settings, click "Sync" or "Sync all", and verify logs in `logs/sync_*.log`.

## Management commands (VPS)

| Command | Description |
|---------|-------------|
| `sync_orders_vps` | Delivery orders (DOs starting with "1") |
| `sync_non_one_orders_vps` | Non-one delivery orders |
| `sync_invoices_vps` | Invoice numbers |
| `sync_cancelled_orders_vps` | Cancelled order status |
| `sync_all_vps` | Delivery orders + non-one + invoices (one cron covers all) |

All commands log to `logs/sync_<entity>.log` with RotatingFileHandler.

## Error handling

If the SSH tunnel is down, API calls will fail with:

```
RuntimeError: Cannot connect to API. Is the SSH tunnel running?
```

Check that the tunnel is running on the PC and that `API_BASE_HOST` is set to `http://localhost:8443` on the VPS.
