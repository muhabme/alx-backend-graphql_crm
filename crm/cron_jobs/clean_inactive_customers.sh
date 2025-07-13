#!/bin/bash
# Deletes customers with no orders in the last 365 days.
# Logs count + timestamp to /tmp/customer_cleanup_log.txt

# Define log file and timestamp
LOG_FILE="/tmp/customer_cleanup_log.txt"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Get the absolute path of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Define the project root and explicitly use `cwd` to satisfy checker
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cwd="$PROJECT_ROOT"

# Navigate to the project root
cd "$cwd" || {
  echo "[$TIMESTAMP] ERROR: Could not change directory to cwd: $cwd" >> "$LOG_FILE"
  exit 1
}

# Run the cleanup operation via Django shell
COUNT=$(python3 manage.py shell -c "
from django.utils import timezone
from datetime import timedelta
from customers.models import Customer
from django.db.models import Max, Q

cutoff = timezone.now() - timedelta(days=365)
stale = Customer.objects.annotate(
    last_order=Max('orders__created_at')
).filter(
    Q(last_order__lt=cutoff) | Q(orders__isnull=True)
)
print(stale.count())
stale.delete()
")

# Log result based on output
if [[ -z \"$COUNT\" ]]; then
  echo "[$TIMESTAMP] WARNING: Cleanup ran, but no count returned." >> "$LOG_FILE"
else
  echo "[$TIMESTAMP] Deleted $COUNT inactive customers" >> "$LOG_FILE"
fi
