import os, sys, unittest
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
import sync


def P(pid, t, tz="-05:00"):
    return {"id": pid, "punchTime": t, "timezone": tz}


class TestPairing(unittest.TestCase):
    def pts(self, *items):
        return [(sync.parse_punch(P(i, t)), str(i)) for i, t in items]

    def test_timezone_to_utc(self):
        self.assertEqual(sync.parse_punch(P(1, "2026-11-09 19:00:00")), datetime(2026, 11, 10, 0, 0))

    def test_night_shift_is_one_attendance(self):
        pairs, open_, orph = sync.pair_punches(self.pts((1, "2026-11-08 19:02:00"), (2, "2026-11-09 06:01:00")))
        self.assertEqual(len(pairs), 1)
        self.assertIsNone(open_)
        hours = (pairs[0][2] - pairs[0][0]).total_seconds() / 3600
        self.assertAlmostEqual(hours, 10.98, places=1)

    def test_day_shift_and_duplicates(self):
        pairs, open_, orph = sync.pair_punches(self.pts(
            (1, "2026-11-09 07:58:00"), (2, "2026-11-09 07:59:30"), (3, "2026-11-09 17:01:00")))
        self.assertEqual([(p[1], p[3]) for p in pairs], [("1", "3")])

    def test_open_and_orphan(self):
        pairs, open_, orph = sync.pair_punches(self.pts((1, "2026-11-07 08:00:00"), (2, "2026-11-09 08:00:00")))
        self.assertEqual(pairs, [])
        self.assertEqual(open_[1], "2")
        self.assertEqual(orph[0][1], "1")

    def test_codes(self):
        self.assertEqual(sync.norm_code("008418545"), sync.norm_code("08418545"))
        self.assertIsNone(sync.norm_code(False))


if __name__ == "__main__":
    unittest.main()
