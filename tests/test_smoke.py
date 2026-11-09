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


##### CR-01 tests
    # CR-01: PRICING, student discount applies to merchandise only, not the express fee
    def test_express_student_discount_excludes_fee(self):
        quote = self.service.quote("student", [{"product_id": "hoodie", "quantity": 2}], "express")
        self.assertEqual(quote["subtotal_cents"], 8000)
        self.assertEqual(quote["discount_cents"], 800)   # 10% of 8000 only, not of 9200
        self.assertEqual(quote["delivery_cents"], 1200)
        self.assertEqual(quote["total_cents"], 8400)

    # CR-01: PRICING, free-delivery threshold never waives the express fee
    def test_express_fee_never_waived(self):
        quote = self.service.quote("regular", [{"product_id": "hoodie", "quantity": 3}], "express")
        self.assertEqual(quote["subtotal_cents"], 12000)   # over the $100 free-delivery threshold
        self.assertEqual(quote["delivery_cents"], 1200)
        self.assertEqual(quote["total_cents"], 13200)

    # CR-01: REGRESSION, standard delivery threshold unchanged
    def test_standard_delivery_threshold_unchanged(self):
        # 9500 subtotal: under the threshold, so the $6.00 fee applies
        below = self.service.quote("regular", [
            {"product_id": "hoodie", "quantity": 2},
            {"product_id": "mug", "quantity": 1},
        ], "delivery")
        self.assertEqual(below["delivery_cents"], 600)
        self.assertEqual(below["total_cents"], 10100)
        # 10000 subtotal: at the threshold, so delivery is free
        at = self.service.quote("regular", [
            {"product_id": "hoodie", "quantity": 2},
            {"product_id": "mug", "quantity": 1},
            {"product_id": "notebook", "quantity": 1},
        ], "delivery")
        self.assertEqual(at["delivery_cents"], 0)
        self.assertEqual(at["total_cents"], 10000)

    # CR-01: LIFECYCLE, express order survives retrieval, reload, and cancel
    def test_express_order_persists_and_cancels(self):
        stock_before = self.service.catalog()
        order = self.service.place_order("student", [{"product_id": "hoodie", "quantity": 2}], "express")
        self.assertEqual(order["total_cents"], 8400)
        reopened = OrderService(self.path).get_order(order["order_id"])
        self.assertEqual(reopened, order)
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        for key in ("fulfillment", "items", "delivery_cents", "discount_cents", "total_cents"):
            self.assertEqual(cancelled[key], order[key])
        self.assertEqual(self.service.catalog(), stock_before)

if __name__ == "__main__":
    unittest.main()
