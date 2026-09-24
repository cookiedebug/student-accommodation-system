import unittest

from app import app


class AccommodationFilterTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_page_combined_room_type_and_price_filters(self):
        response = self.client.get('/?room_type=Single&max_price=800')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sunrise Hostel', response.data)

    def test_room_type_price_filter_applies_to_selected_room_type(self):
        response = self.client.get('/?room_type=Single&max_price=700')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Sunrise Hostel', response.data)


if __name__ == '__main__':
    unittest.main()
