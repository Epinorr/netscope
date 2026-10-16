import unittest
from netscope.diagnostics import CheckResult, build_report, report_as_text


class ReportTests(unittest.TestCase):
    def test_report_counts_and_text(self):
        results = [
            CheckResult("dns", "DNS", "PASS", "Resolved", "example.com", 12),
            CheckResult("tcp", "TCP", "FAIL", "Connection failed", "timeout", 40),
        ]
        report = build_report(results)
        self.assertEqual(report.summary["PASS"], 1)
        self.assertEqual(report.summary["FAIL"], 1)
        text = report_as_text(report)
        self.assertIn("NETSCOPE NETWORK DIAGNOSTICS REPORT", text)
        self.assertIn("[FAIL] TCP", text)
        self.assertIn("PRIVACY NOTE", text)

    def test_report_redaction_masks_private_ips_and_ssid(self):
        results = [
            CheckResult(
                "wifi",
                "Wi-Fi status",
                "PASS",
                "Connected",
                "SSID : MyHomeWiFi\nIPv4 Address: 192.168.1.45\nMAC: AA-BB-CC-DD-EE-FF",
                18,
            ),
        ]
        report = build_report(results)
        redacted = report_as_text(report, redact=True)
        self.assertNotIn("192.168.1.45", redacted)
        self.assertNotIn("MyHomeWiFi", redacted)
        self.assertNotIn("AA-BB-CC-DD-EE-FF", redacted)
        self.assertIn("[PRIVATE-IP]", redacted)
        self.assertIn("[REDACTED-SSID]", redacted)
        self.assertIn("[REDACTED-MAC]", redacted)


if __name__ == "__main__":
    unittest.main()