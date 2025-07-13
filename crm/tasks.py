"""
Celery tasks for CRM application.
"""

import os
import django
from datetime import datetime
from celery import shared_task

# Setup Django environment explicitly for standalone task run (if needed)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
django.setup()

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

LOG_FILE = "/tmp/crm_report_log.txt"
GRAPHQL_URL = "http://localhost:8000/graphql"


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def generate_crm_report(self):
    """
    Generate a weekly CRM report using GraphQL queries.
    Fetches total customers, orders, and revenue from the full lists,
    then logs to a file with timestamp.
    Retries on failure up to 3 times with 5 minutes delay.
    """
    try:
        transport = RequestsHTTPTransport(
            url=GRAPHQL_URL,
            verify=True,
            retries=3,
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)

        # Query fetching all customers and orders (matches your schema)
        query = gql("""
            query {
                allCustomers: allCustomers {
                    edges {
                        node {
                            id
                        }
                    }
                }
                allOrders: allOrders {
                    edges {
                        node {
                            id
                            totalAmount
                        }
                    }
                }
            }
        """)

        result = client.execute(query)

        customers = result.get('allCustomers', {}).get('edges', [])
        orders = result.get('allOrders', {}).get('edges', [])

        total_customers = len(customers)
        total_orders = len(orders)
        total_revenue = sum(float(order['node']['totalAmount']) for order in orders)

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report_message = (
            f"{timestamp} - Report: {total_customers} customers, "
            f"{total_orders} orders, {total_revenue:.2f} revenue."
        )

        with open(LOG_FILE, 'a') as log_file:
            log_file.write(report_message + '\n')

        print(f"CRM Report generated: {report_message}")
        return report_message

    except Exception as exc:
        error_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ERROR generating CRM report: {exc}"
        try:
            with open(LOG_FILE, 'a') as log_file:
                log_file.write(error_message + '\n')
        except Exception as log_exc:
            print(f"Failed to write error log: {log_exc}")

        print(error_message)

        # Retry with exponential backoff / delay
        raise self.retry(exc=exc, countdown=60 * 5)


@shared_task
def test_celery():
    """Test task to verify Celery is working."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = f"{timestamp} - Celery test task executed successfully"
    try:
        with open("/tmp/celery_test_log.txt", "a") as log_file:
            log_file.write(message + "\n")
    except Exception as exc:
        print(f"Failed to write test log: {exc}")

    print(message)
    return message
