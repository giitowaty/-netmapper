import json
import os
import tempfile
import unittest

from netmapper.gps import Fix, parse_tpv
from netmapper.mapper import render_map
from netmapper.store import Store
from netmapper.wifi import Network


def net(bssid, ssid, signal, security="WPA2"):
    return Network(
        bssid=bssid,
        ssid=ssid,
        freq=2437,
        channel=6,
        band="2.4 GHz",
        signal=signal,
        security=security,
    )


class ParseTpvTests(unittest.TestCase):
    def test_2d_fix(self):
        line = '{"class":"TPV","mode":3,"lat":52.1,"lon":21.0,"alt":110.5}'
        self.assertEqual(parse_tpv(line), Fix(52.1, 21.0, 110.5))

    def test_no_fix_is_ignored(self):
        self.assertIsNone(parse_tpv('{"class":"TPV","mode":1}'))

    def test_other_messages_are_ignored(self):
        self.assertIsNone(parse_tpv('{"class":"SKY"}'))
        self.assertIsNone(parse_tpv("not json"))


class StoreTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.path)

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_one_entry_per_bssid_at_strongest_location(self):
        self.store.add([net("aa:aa:aa:aa:aa:01", "Cafe", -80)], Fix(52.0, 21.0))
        self.store.add([net("aa:aa:aa:aa:aa:01", "Cafe", -50)], Fix(52.5, 21.5))
        self.store.add([net("aa:aa:aa:aa:aa:01", "Cafe", -70)], Fix(52.9, 21.9))

        [row] = self.store.networks()
        self.assertEqual(row["seen"], 3)
        self.assertEqual(row["signal"], -50)
        self.assertEqual((row["lat"], row["lon"]), (52.5, 21.5))
        self.assertLessEqual(row["first_seen"], row["last_seen"])

    def test_distinct_bssids_stay_separate(self):
        self.store.add(
            [net("aa:aa:aa:aa:aa:01", "A", -40), net("aa:aa:aa:aa:aa:02", "B", -40)],
            Fix(52.0, 21.0),
        )
        self.assertEqual(len(self.store.networks()), 2)


class MapperTests(unittest.TestCase):
    def test_ssid_cannot_break_out_of_script(self):
        evil = '</script><script>alert("x")</script><!--'
        page = render_map([{
            "bssid": "aa:aa:aa:aa:aa:01",
            "ssid": evil,
            "security": "Open",
            "band": "2.4 GHz",
            "channel": 1,
            "signal": -40,
            "lat": 52.0,
            "lon": 21.0,
            "seen": 1,
            "first_seen": "t",
            "last_seen": "t",
        }])
        self.assertNotIn("</script><script>alert", page)
        self.assertNotIn("<!--", page.split("const NETWORKS = ", 1)[1])

    def test_data_is_embedded_as_valid_json(self):
        page = render_map([{"ssid": "Net", "lat": 1.0, "lon": 2.0, "security": "WPA3"}])
        data_line = [l for l in page.splitlines() if l.startswith("const NETWORKS = ")][0]
        payload = data_line[len("const NETWORKS = "):].rstrip(";")
        self.assertEqual(json.loads(payload)[0]["ssid"], "Net")


if __name__ == "__main__":
    unittest.main()
