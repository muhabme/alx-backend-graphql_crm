#!/usr/bin/env python3
"""
Send daily order reminders via GraphQL.

Runs from cron every day at 08:00.
Requires: gql[requests]  (pip install gql[requests])
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

GRAPHQL_URL = "http://localhost:8000/graphql"
LOG_FILE = "/tmp/order_reminders_log.txt"

# Build the date range filter
since = datetime.now(timezone.utc) - timedelta(days=7)

transport = RequestsHTTPTransport(
    url=GRAPHQL_URL,
    verify=True,
    retries=3,
    timeout=10,
)

client = Client(transport=transport, fetch_schema_from_transport=False)

query = gql("""
query GetPendingOrders($since: DateTime!) {
  orders(orderDate_Gte: $since) {
    id
    customer {
      email
    }
  }
}
""")

try:
    result = client.execute(query, variable_values={"since": since.isoformat()})
    orders = result.get("orders", [])

    with open(LOG_FILE, "a") as log:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for order in orders:
            log.write(f"{ts} - Order #{order['id']} - {order['customer']['email']}\n")

    print("Order reminders processed!")
except Exception as exc:
    # Any failure exits non-zero so cron can alert via mail.
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)
