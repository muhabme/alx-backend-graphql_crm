"""
Heartbeat job for django-crontab.
Runs every 5 minutes.
"""

import datetime
import os
import sys
from pathlib import Path

# Ensure Django settings are available when run via cron
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")

import django
django.setup()

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

LOG_FILE = "/tmp/crm_heartbeat_log.txt"

def log_crm_heartbeat():
    """
    Append a heartbeat line to the log file.
    Optionally hit the GraphQL 'hello' field to confirm endpoint health.
    """
    now = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    line = f"{now} CRM is alive"

    # Set up gql client for GraphQL query
    transport = RequestsHTTPTransport(
        url="http://localhost:8000/graphql",
        verify=True,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)

    query = gql("{ hello }")

    try:
        response = client.execute(query)
        # If 'hello' key exists in response, consider OK
        if "hello" in response:
            gql_status = "GraphQL OK"
        else:
            gql_status = "GraphQL responded without 'hello' field"
    except Exception as exc:
        gql_status = f"GraphQL ERROR ({exc})"

    line += f" - {gql_status}\n"

    with open(LOG_FILE, "a") as f:
        f.write(line)


# Allow standalone execution for quick test
if __name__ == "__main__":
    log_crm_heartbeat()


LOG_FILE_LOW_STOCK = "/tmp/low_stock_updates_log.txt"

def update_low_stock():
    """
    Cron job to run a GraphQL mutation to restock low-stock products (stock < 10).
    Logs updated products and messages to a log file.
    """
    now = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")

    transport = RequestsHTTPTransport(
        url="http://localhost:8000/graphql",
        verify=True,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)

    mutation = gql("""
    mutation {
      updateLowStockProducts {
        updatedProducts {
          id
          name
          stock
        }
        message
      }
    }
    """)

    try:
        response = client.execute(mutation)
        updated_products = response['updateLowStockProducts']['updatedProducts']
        message = response['updateLowStockProducts']['message']

        log_lines = [f"{now} - {message}"]
        for product in updated_products:
            log_lines.append(f"Product: {product['name']}, Stock: {product['stock']}")

        with open(LOG_FILE_LOW_STOCK, "a") as f:
            f.write("\n".join(log_lines) + "\n")

    except Exception as e:
        with open(LOG_FILE_LOW_STOCK, "a") as f:
            f.write(f"{now} - ERROR executing mutation: {e}\n")
