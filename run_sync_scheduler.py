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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Configuration
SYNC_INTERVAL = 120  # 2 minutes in seconds
DAYS_BACK = 3  # Number of days to sync
MANAGE_PY_PATH = os.path.join(os.path.dirname(__file__), 'manage.py')


def run_sync():
    """Run the sync command"""
    try:
        logger.info("=" * 60)
        logger.info(f"Starting sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run the sync command
        result = subprocess.run(
            [sys.executable, MANAGE_PY_PATH, 'sync_delivery_orders', '--days-back', str(DAYS_BACK)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace encoding errors instead of failing
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            logger.info("Sync completed successfully")
            if result.stdout:
                # Log important output lines
                for line in result.stdout.split('\n'):
                    if '[OK]' in line or 'Successfully' in line or 'Updated' in line or 'Created' in line or 'Sync successful' in line:
                        logger.info(f"  {line.strip()}")
        else:
            logger.error(f"Sync failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")
            if result.stdout:
                logger.error(f"Output: {result.stdout}")
        
        logger.info(f"Sync finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        logger.error("Sync command timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"Error running sync: {str(e)}", exc_info=True)
        return False


def main():
    """Main scheduler loop"""
    logger.info("=" * 60)
    logger.info("Sync Scheduler Started")
    logger.info(f"Sync interval: {SYNC_INTERVAL} seconds ({SYNC_INTERVAL // 60} minutes)")
    logger.info(f"Days back: {DAYS_BACK}")
    logger.info(f"Manage.py path: {MANAGE_PY_PATH}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    # Verify manage.py exists
    if not os.path.exists(MANAGE_PY_PATH):
        logger.error(f"Error: manage.py not found at {MANAGE_PY_PATH}")
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
        sys.exit(1)


if __name__ == '__main__':
    main()
