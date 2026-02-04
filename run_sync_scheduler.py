"""
Scheduler script to run sync_delivery_orders command every 2 minutes
Can be run as a background service or daemon
"""
import os
import sys
import time
import subprocess
import logging
from datetime import datetime

# Fix Windows encoding issues
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Setup logging
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, 'scheduler.log')

# Remove all existing handlers to avoid duplicates
logging.getLogger().handlers = []

# Configure logging with file handler (pythonw doesn't have stdout)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', mode='a'),  # Append mode
    ],
    force=True  # Force reconfiguration
)

# Only add StreamHandler if running with python (not pythonw)
if sys.executable.endswith('python.exe'):
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

logger = logging.getLogger(__name__)

# Configuration
SYNC_INTERVAL = 120  # 2 minutes in seconds
DAYS_BACK = 3  # Number of days to sync
MANAGE_PY_PATH = os.path.join(os.path.dirname(__file__), 'manage.py')


def run_sync():
    """Run the sync commands (DO sync first, then invoice sync)"""
    try:
        logger.info("=" * 60)
        logger.info(f"Starting sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Run DO sync command
        logger.info("Running DO sync...")
        do_sync_result = subprocess.run(
            [sys.executable, MANAGE_PY_PATH, 'sync_delivery_orders', '--days-back', str(DAYS_BACK)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace encoding errors instead of failing
            timeout=300  # 5 minute timeout
        )
        
        do_success = False
        if do_sync_result.returncode == 0:
            logger.info("DO sync completed successfully")
            if do_sync_result.stdout:
                # Log important output lines
                for line in do_sync_result.stdout.split('\n'):
                    if '[OK]' in line or 'Successfully' in line or 'Updated' in line or 'Created' in line or 'Sync successful' in line:
                        logger.info(f"  {line.strip()}")
            do_success = True
        else:
            logger.error(f"DO sync failed with return code {do_sync_result.returncode}")
            if do_sync_result.stderr:
                logger.error(f"Error: {do_sync_result.stderr}")
            if do_sync_result.stdout:
                # Log all output for debugging, especially error details
                logger.error("DO sync output:")
                for line in do_sync_result.stdout.split('\n'):
                    if line.strip():
                        # Highlight error lines
                        if '[ERROR]' in line or 'Error' in line or 'error' in line or 'HTTP Error' in line:
                            logger.error(f"  {line.strip()}")
                        else:
                            logger.info(f"  {line.strip()}")
        
        # Step 2: Run invoice sync command (after DO sync)
        logger.info("Running invoice sync...")
        invoice_sync_result = subprocess.run(
            [sys.executable, MANAGE_PY_PATH, 'sync_do_invoices', '--days-back', str(DAYS_BACK)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace encoding errors instead of failing
            timeout=300  # 5 minute timeout
        )
        
        invoice_success = False
        if invoice_sync_result.returncode == 0:
            logger.info("Invoice sync completed successfully")
            if invoice_sync_result.stdout:
                # Log important output lines
                for line in invoice_sync_result.stdout.split('\n'):
                    if '[OK]' in line or 'Successfully' in line or 'Updated' in line or 'Sync successful' in line:
                        logger.info(f"  {line.strip()}")
            invoice_success = True
        else:
            logger.error(f"Invoice sync failed with return code {invoice_sync_result.returncode}")
            if invoice_sync_result.stderr:
                logger.error(f"Error: {invoice_sync_result.stderr}")
            if invoice_sync_result.stdout:
                # Log all output for debugging, especially error details
                logger.error("Invoice sync output:")
                for line in invoice_sync_result.stdout.split('\n'):
                    if line.strip():
                        # Highlight error lines
                        if '[ERROR]' in line or 'Error' in line or 'error' in line or 'HTTP Error' in line:
                            logger.error(f"  {line.strip()}")
                        else:
                            logger.info(f"  {line.strip()}")
        
        logger.info(f"Sync finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"DO sync: {'Success' if do_success else 'Failed'}, Invoice sync: {'Success' if invoice_success else 'Failed'}")
        logger.info("=" * 60)
        
        # Return True only if both syncs succeeded
        return do_success and invoice_success
        
    except subprocess.TimeoutExpired:
        logger.error("Sync command timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"Error running sync: {str(e)}", exc_info=True)
        return False


def main():
    """Main scheduler loop"""
    try:
        logger.info("=" * 60)
        logger.info("Sync Scheduler Started (DO Sync + Invoice Sync)")
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Script directory: {os.path.dirname(__file__)}")
        logger.info(f"Sync interval: {SYNC_INTERVAL} seconds ({SYNC_INTERVAL // 60} minutes)")
        logger.info(f"Days back: {DAYS_BACK}")
        logger.info(f"Manage.py path: {MANAGE_PY_PATH}")
        logger.info("Sync sequence: 1) DO Sync, 2) Invoice Sync")
        logger.info("=" * 60)
        
        # Verify manage.py exists
        if not os.path.exists(MANAGE_PY_PATH):
            logger.error(f"Error: manage.py not found at {MANAGE_PY_PATH}")
            logger.error(f"Current directory: {os.getcwd()}")
            logger.error(f"Script directory: {os.path.dirname(__file__)}")
            sys.exit(1)
        
        logger.info(f"Verified: manage.py exists at {MANAGE_PY_PATH}")
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}", exc_info=True)
        sys.exit(1)
    
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    try:
        while True:
            success = run_sync()
            
            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"Too many consecutive failures ({max_consecutive_failures}). Stopping scheduler.")
                    sys.exit(1)
            
            # Wait for next sync
            logger.info(f"Waiting {SYNC_INTERVAL} seconds until next sync...")
            time.sleep(SYNC_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("\nScheduler stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error in scheduler: {str(e)}", exc_info=True)
        # Log full traceback for debugging
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == '__main__':
    main()
