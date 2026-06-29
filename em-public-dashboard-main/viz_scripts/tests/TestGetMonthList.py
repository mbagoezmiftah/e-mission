import arrow
import unittest

class TestGetMonthList(unittest.TestCase):
    def test_same_month(self):
        start_date = arrow.get(2020, 5, 1)
        end_date = arrow.get(2020, 5, 1)
        month_range = list(arrow.Arrow.range('month', start_date, end_date))
        self.assertEqual(len(month_range), 1)
        self.assertEqual([m.year for m in month_range], [2020])
        self.assertEqual([m.month for m in month_range], [5])

    def test_same_year(self):
        start_date = arrow.get(2020, 5, 1)
        end_date = arrow.get(2020, 10, 1)
        month_range = list(arrow.Arrow.range('month', start_date, end_date))
        self.assertEqual([m.year for m in month_range], [2020] * 6)
        self.assertEqual([m.month for m in month_range], list(range(5,11)))

    def test_less_than_twelve_months_spans_two_years(self):
        start_date = arrow.get(2020, 7, 1)
        end_date = arrow.get(2021, 5, 1)
        month_range = list(arrow.Arrow.range('month', start_date, end_date))
        self.assertEqual([m.year for m in month_range[:6]], [2020] * 6)
        self.assertEqual([m.year for m in month_range[6:]], [2021] * 5)
        self.assertEqual([m.month for m in month_range[:6]], list(range(7, 13)))
        self.assertEqual([m.month for m in month_range[6:]], list(range(1, 6)))

    def test_more_than_twelve_months_spans_two_years(self):
        start_date = arrow.get(2020, 7, 1)
        end_date = arrow.get(2021, 9, 1)
        month_range = list(arrow.Arrow.range('month', start_date, end_date))
        self.assertEqual([m.year for m in month_range[:6]], [2020] * 6)
        self.assertEqual([m.year for m in month_range[6:]], [2021] * 9)
        self.assertEqual([m.month for m in month_range[:6]], list(range(7, 13)))
        self.assertEqual([m.month for m in month_range[6:]], list(range(1, 10)))

if __name__ == '__main__':
    unittest.main()
