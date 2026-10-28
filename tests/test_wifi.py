import unittest

from netmapper.wifi import channel_from_freq, band_from_freq, classify, parse_scan


def bss(bssid, *lines):
    return "\n".join([f"BSS {bssid}(on wlan0)", *(f"\t{line}" for line in lines)])


class ClassifyTests(unittest.TestCase):
    def test_open(self):
        self.assertEqual(classify(False, None, None), "Open")

    def test_wep(self):
        self.assertEqual(classify(True, None, None), "WEP")

    def test_wpa(self):
        self.assertEqual(classify(True, None, {"PSK"}), "WPA")

    def test_wpa_enterprise(self):
        self.assertEqual(classify(True, None, {"802.1X"}), "WPA-Enterprise")

    def test_wpa2(self):
        self.assertEqual(classify(True, {"PSK"}, None), "WPA2")

    def test_wpa2_sha256_variant(self):
        self.assertEqual(classify(True, {"PSK/SHA-256"}, None), "WPA2")

    def test_wpa3(self):
        self.assertEqual(classify(True, {"SAE"}, None), "WPA3")

    def test_wpa2_wpa3_transition(self):
        self.assertEqual(classify(True, {"PSK", "SAE"}, None), "WPA2/WPA3")

    def test_wpa2_enterprise(self):
        self.assertEqual(classify(True, {"802.1X"}, None), "WPA2-Enterprise")

    def test_wpa3_enterprise(self):
        self.assertEqual(classify(True, {"802.1X/SUITE-B-192"}, None), "WPA3-Enterprise")

    def test_enhanced_open(self):
        self.assertEqual(classify(False, {"OWE"}, None), "OWE")

    def test_rsn_both_wpa_and_rsn_prefers_rsn(self):
        self.assertEqual(classify(True, {"PSK"}, {"PSK"}), "WPA2")


class FrequencyTests(unittest.TestCase):
    def test_2_4ghz_channels(self):
        self.assertEqual(channel_from_freq(2412), 1)
        self.assertEqual(channel_from_freq(2437), 6)
        self.assertEqual(channel_from_freq(2484), 14)

    def test_5ghz_channel(self):
        self.assertEqual(channel_from_freq(5180), 36)

    def test_6ghz_channel(self):
        self.assertEqual(channel_from_freq(5955), 1)

    def test_bands(self):
        self.assertEqual(band_from_freq(2437), "2.4 GHz")
        self.assertEqual(band_from_freq(5180), "5 GHz")
        self.assertEqual(band_from_freq(6115), "6 GHz")
        self.assertEqual(band_from_freq(0), "unknown")


class ParseScanTests(unittest.TestCase):
    def test_parses_fields_and_security(self):
        text = "\n".join([
            bss(
                "00:11:22:33:44:55",
                "freq: 2437.0",
                "capability: ESS Privacy ShortSlotTime (0x0411)",
                "signal: -41.00 dBm",
                "SSID: HomeWifi",
                "RSN:\t * Version: 1",
                "\t * Authentication suites: PSK",
            ),
        ])
        [net] = parse_scan(text)
        self.assertEqual(net.bssid, "00:11:22:33:44:55")
        self.assertEqual(net.ssid, "HomeWifi")
        self.assertEqual(net.freq, 2437)
        self.assertEqual(net.channel, 6)
        self.assertEqual(net.band, "2.4 GHz")
        self.assertEqual(net.signal, -41.0)
        self.assertEqual(net.security, "WPA2")

    def test_multiple_networks_and_mixed_security(self):
        text = "\n".join([
            bss("aa:bb:cc:dd:ee:01", "freq: 2412.0", "capability: ESS", "signal: -80.00 dBm", "SSID: CoffeeShop"),
            bss("aa:bb:cc:dd:ee:02", "freq: 5180.0", "capability: ESS Privacy", "signal: -70.00 dBm", "SSID: Office-5G", "RSN:\t * Version: 1", "\t * Authentication suites: SAE"),
            bss("aa:bb:cc:dd:ee:03", "freq: 2462.0", "capability: ESS Privacy", "signal: -90.00 dBm", "SSID: OldRouter", "WPA:\t * Version: 1", "\t * Authentication suites: PSK"),
            bss("aa:bb:cc:dd:ee:04", "freq: 2437.0", "capability: ESS Privacy", "signal: -60.00 dBm", "SSID: ", "RSN:\t * Authentication suites: PSK SAE"),
            bss("aa:bb:cc:dd:ee:05", "freq: 2437.0", "capability: ESS Privacy", "signal: -50.00 dBm", "SSID: OldWep"),
        ])
        nets = {n.ssid: n for n in parse_scan(text)}
        self.assertEqual(nets["CoffeeShop"].security, "Open")
        self.assertEqual(nets["Office-5G"].security, "WPA3")
        self.assertEqual(nets["Office-5G"].band, "5 GHz")
        self.assertEqual(nets["OldRouter"].security, "WPA")
        self.assertEqual(nets[""].security, "WPA2/WPA3")
        self.assertEqual(nets["OldWep"].security, "WEP")

    def test_hidden_ssid_is_empty_string(self):
        text = bss("aa:bb:cc:dd:ee:06", "freq: 2437.0", "capability: ESS", "SSID: ")
        [net] = parse_scan(text)
        self.assertEqual(net.ssid, "")

    def test_empty_output(self):
        self.assertEqual(parse_scan(""), [])


if __name__ == "__main__":
    unittest.main()
