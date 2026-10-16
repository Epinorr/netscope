import unittest
from types import SimpleNamespace
from netscope.repairs import analyse_results, recommended_fixes, FIX_BY_ID


def make_results(**statuses):
    return [SimpleNamespace(id=key, status=value) for key, value in statuses.items()]


class RepairAnalysisTests(unittest.TestCase):
    def test_dns_failure_recommends_only_dns_cache_flush_when_ip_works(self):
        results = make_results(internet_ip="PASS", dns="FAIL", gateway="PASS", https="FAIL", tcp="PASS")
        self.assertEqual(recommended_fixes(results), ["flush_dns"])
        findings = analyse_results(results)
        self.assertTrue(any(f["title"] == "DNS lookup failed" for f in findings))

    def test_missing_gateway_recommends_dhcp_renew(self):
        results = make_results(gateway="FAIL", internet_ip="FAIL", dns="FAIL", https="FAIL", tcp="FAIL")
        self.assertIn("renew_dhcp", recommended_fixes(results))

    def test_no_unnecessary_fix_when_core_checks_pass(self):
        results = make_results(gateway="PASS", internet_ip="PASS", dns="PASS", https="PASS", tcp="PASS", proxy="INFO")
        self.assertEqual(recommended_fixes(results), [])
        self.assertTrue(analyse_results(results))

    def test_advanced_repairs_are_not_auto_recommended(self):
        results = make_results(gateway="PASS", internet_ip="PASS", dns="FAIL", https="FAIL", tcp="FAIL", proxy="WARN")
        self.assertNotIn("winsock_reset", recommended_fixes(results))
        self.assertNotIn("tcpip_reset", recommended_fixes(results))
        self.assertIn("flush_dns", recommended_fixes(results))

    def test_ping_failure_is_not_called_an_outage_when_https_works(self):
        results = make_results(gateway="PASS", internet_ip="FAIL", dns="PASS", https="PASS", tcp="PASS")
        findings = analyse_results(results)
        titles = [item["title"] for item in findings]
        self.assertIn("Ping may be blocked", titles)
        self.assertNotIn("Public IP reachability failed", titles)
        # Ensure duplicate ping findings are not emitted simultaneously
        self.assertEqual(len([t for t in titles if "Ping" in t or "HTTPS works" in t]), 1)

    def test_fix_catalog_contains_explicit_restart_metadata(self):
        self.assertTrue(FIX_BY_ID["winsock_reset"].reboot)
        self.assertTrue(FIX_BY_ID["tcpip_reset"].requires_admin)
        self.assertIn("arp_flush", FIX_BY_ID)


if __name__ == "__main__":
    unittest.main()