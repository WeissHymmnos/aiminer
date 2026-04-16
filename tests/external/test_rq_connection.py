import os
import unittest

import rqdatac as rq
from dotenv import load_dotenv


load_dotenv()


class TestRiceQuantConnection(unittest.TestCase):
    def test_rq_credentials_available_and_connectable(self):
        token = os.getenv("RQ_TOKEN")
        user = os.getenv("RQ_USER")
        password = os.getenv("RQ_PASS")

        if not (token or (user and password)):
            self.skipTest("RiceQuant credentials are not configured in .env.")

        if token:
            try:
                rq.init(token=token.strip())
                self.assertTrue(rq.initialized())
                return
            except Exception as exc:
                if not (user and password):
                    self.fail(f"RiceQuant token authentication failed: {exc}")

        if user and password:
            try:
                rq.init(username=user.strip(), password=password.strip())
                self.assertTrue(rq.initialized())
                return
            except Exception as exc:
                self.fail(f"RiceQuant password authentication failed: {exc}")


if __name__ == "__main__":
    unittest.main()
