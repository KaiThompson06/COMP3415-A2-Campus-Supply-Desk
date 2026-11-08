"""A small starting test suite for the order desk."""

from pathlib import Path
import tempfile
import unittest

from supplydesk.service import OrderService


class OrderSmokeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"
        self.service = OrderService(self.path)

    def test_regular_pickup_quote(self):
        quote = self.service.quote("regular", [{"product_id": "notebook", "quantity": 2}])
        self.assertEqual(quote["subtotal_cents"], 1000)
        self.assertEqual(quote["discount_cents"], 0)
        self.assertEqual(quote["delivery_cents"], 0)
        self.assertEqual(quote["total_cents"], 1000)

    def test_student_delivery_quote(self):
        quote = self.service.quote("student", [{"product_id": "hoodie", "quantity": 2}], "delivery")
        self.assertEqual(quote["discount_cents"], 800)
        self.assertEqual(quote["delivery_cents"], 600)
        self.assertEqual(quote["total_cents"], 7800)

    def test_order_can_be_reopened(self):
        order = self.service.place_order("regular", [{"product_id": "mug", "quantity": 1}])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(OrderService(self.path).get_order(order["order_id"]), order)

    def test_cancel_order_restores_stock(self):
        before = self.service.catalog()
        order = self.service.place_order("regular", [{"product_id": "pen-pack", "quantity": 2}])
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(self.service.catalog(), before)

# NORMAL BEHAVIOR TESTS
# test if the program allows a customer to place an order with valid inputs
    def test_place_order_with_valid_inputs(self):
        order = self.service.place_order("regular", [{"product_id": "notebook", "quantity": 2}])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(order["customer_type"], "regular")
        self.assertEqual(order["fulfillment"], "pickup")
        self.assertEqual(len(order["items"]), 1)
        self.assertEqual(order["items"][0]["product_id"], "notebook")
        self.assertEqual(order["items"][0]["quantity"], 2)


# BOUNDARY TESTS
# test if the program allows a customer to place an order with zero quantity
    def test_zero_quantity_order(self):
        with self.assertRaises(ValueError):
            self.service.place_order("regular", [{"product_id": "notebook", "quantity": 0}])

    def test_over_order_single_line(self):
        with self.assertRaises(ValueError):
            self.service.place_order("regular", [{"product_id": "hoodie", "quantity": 8}])

# test if the program allows a customer to over order more than the available stock with multiple lines
    def test_over_order_multiple_lines(self):
        # print(self.service.catalog()[2]["stock"])
        with self.assertRaises(ValueError):
            self.service.place_order("regular", [
                {"product_id": "hoodie", "quantity": 4},
                {"product_id": "hoodie", "quantity": 4}
            ])
            # print(self.service.catalog()[2]["stock"]) # view if stock is within a valid range after the order is placed

# INVALID INPUT TESTS
# test if the program allows an invalid customer type to be used in quote and place_order
    def test_invalid_customer_type(self):
        with self.assertRaises(ValueError):
            self.service.quote("invalid_customer", [{"product_id": "notebook", "quantity": 2}])
        with self.assertRaises(ValueError):
            self.service.place_order("invalid_customer", [{"product_id": "notebook", "quantity": 2}])
# test if the program allows an invalid product_id to be used in quote and place_order
    def test_invalid_product_id(self):
        with self.assertRaises(ValueError):
            self.service.quote("regular", [{"product_id": "invalid_product", "quantity": 2}])
        with self.assertRaises(ValueError):
            self.service.place_order("regular", [{"product_id": "invalid_product", "quantity": 2}])
#test if the program allows an invalid fulfillment type to be used in quote and place_order
    def test_invalid_fulfillment_type(self):
        with self.assertRaises(ValueError):
            self.service.quote("regular", [{"product_id": "notebook", "quantity": 2}], "invalid_fulfillment")
        with self.assertRaises(ValueError):
            self.service.place_order("regular", [{"product_id": "notebook", "quantity": 2}], "invalid_fulfillment")

# BEHAVIOUR IMPORTANT TO PRESERVE TESTS

# ensure that quote and place_order are consistent with each other 
    def test_quote_and_place_order_consistency(self):
        quote = self.service.quote("regular", [{"product_id": "notebook", "quantity": 2}])
        order = self.service.place_order("regular", [{"product_id": "notebook", "quantity": 2}])
        self.assertEqual(quote["total_cents"], order["total_cents"])
        self.assertEqual(quote["subtotal_cents"], order["subtotal_cents"])
        self.assertEqual(quote["discount_cents"], order["discount_cents"])
        self.assertEqual(quote["delivery_cents"], order["delivery_cents"])


if __name__ == "__main__":
    unittest.main()
