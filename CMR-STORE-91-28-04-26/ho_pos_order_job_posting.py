import xmlrpc.client
import logging
import sys
from datetime import datetime

# Logging setup
logging.basicConfig(
    filename='/home/store1/external_ho_pos_order_job.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logging.info("Job Started successfully")
# Odoo Configuration
url = "http://192.168.168.91/"
db = "SRIKAKULAM"
username = "admin@nhclindia.com"
password = "admin"

try:
    # Authenticate
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, username, password, {})

    if not uid:
        raise Exception("Authentication failed")

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    # Call method
    result = models.execute_kw(
        db,
        uid,
        password,
        'pos.order',
        # 'send_pos_order_data_to_ho',
        # 'get_pos_journal_entry',
        # 'get_pos_crediet_note_issue_journal_entry',
        'call_pos_orders',
        [[]]
    )

    logging.info("Job executed successfully")
    print("Success:", result)

except Exception as e:
    logging.error(f"Job failed: {str(e)}")
    print("Error:", e)
    sys.exit(1)