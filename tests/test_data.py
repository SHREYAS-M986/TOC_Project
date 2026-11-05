"""Comprehensive Test Cases Dataset for Web Content Analyzer (RE vs DFA).

Contains at least 4 positive and 4 negative test cases per pattern,
with formal expected outcomes used for pytest and generating test_cases.md.
"""

TEST_CASES = {
    "email": [
        # Positives
        {
            "input": "test.user@example.com",
            "expected": True,
            "desc": "Standard user email with dot",
        },
        {
            "input": "student123@sub.domain.edu",
            "expected": True,
            "desc": "Subdomain educational email",
        },
        {
            "input": "support-desk_team+info@dept.co.in",
            "expected": True,
            "desc": "Email with plus, hyphen, underscore",
        },
        {
            "input": "admin@portal.gov.in",
            "expected": True,
            "desc": "Government portal email",
        },
        {
            "input": "contact.ugc@nic.in",
            "expected": True,
            "desc": "Indian NIC official email",
        },
        # Negatives
        {
            "input": "notanemail",
            "expected": False,
            "desc": "Plain word without '@' or domain",
        },
        {
            "input": "@missingusername.com",
            "expected": False,
            "desc": "Missing local username before '@'",
        },
        {
            "input": "username@nodot",
            "expected": False,
            "desc": "Domain missing dot and TLD",
        },
        {
            "input": "user@domain.c",
            "expected": False,
            "desc": "TLD shorter than 2 characters",
        },
        {
            "input": "user@.com",
            "expected": False,
            "desc": "Missing domain name before dot",
        },
    ],
    "mobile": [
        # Positives
        {
            "input": "9876543210",
            "expected": True,
            "desc": "Plain 10-digit Indian mobile starting with 9",
        },
        {
            "input": "+91 9876543210",
            "expected": True,
            "desc": "Mobile with +91 country code and space",
        },
        {
            "input": "91-8765432109",
            "expected": True,
            "desc": "Mobile with 91 prefix and hyphen, starting with 8",
        },
        {
            "input": "07123456789",
            "expected": True,
            "desc": "Mobile with 0 trunk prefix, starting with 7",
        },
        {
            "input": "+916234567890",
            "expected": True,
            "desc": "Mobile with +91 without space, starting with 6",
        },
        # Negatives
        {
            "input": "5876543210",
            "expected": False,
            "desc": "Invalid starting digit 5 (Indian mobiles start 6-9)",
        },
        {
            "input": "98765432101",
            "expected": False,
            "desc": "11 digits without prefix (invalid length)",
        },
        {
            "input": "987654",
            "expected": False,
            "desc": "Incomplete mobile number (only 6 digits)",
        },
        {
            "input": "1234567890",
            "expected": False,
            "desc": "Starts with 1 (not an Indian mobile number)",
        },
        {
            "input": "+91 5876543210",
            "expected": False,
            "desc": "+91 prefix with invalid starting digit 5",
        },
    ],
    "date": [
        # Positives
        {
            "input": "31-12-2026",
            "expected": True,
            "desc": "Maximum valid day (31) and month (12) in 2026",
        },
        {
            "input": "01-01-2000",
            "expected": True,
            "desc": "Minimum valid day (01) and month (01) in 2000",
        },
        {
            "input": "15-08-1947",
            "expected": True,
            "desc": "Historical date in 20th century range (1900-2099)",
        },
        {
            "input": "29-02-2024",
            "expected": True,
            "desc": "Valid leap year format date",
        },
        {
            "input": "05-11-2025",
            "expected": True,
            "desc": "Mid-month date in valid format",
        },
        # Negatives
        {
            "input": "32-01-2026",
            "expected": False,
            "desc": "Invalid day 32 (exceeds 31)",
        },
        {
            "input": "03-13-2026",
            "expected": False,
            "desc": "Invalid month 13 (exceeds 12)",
        },
        {
            "input": "00-05-2020",
            "expected": False,
            "desc": "Invalid day 00 (minimum is 01)",
        },
        {
            "input": "15/08/2020",
            "expected": False,
            "desc": "Invalid separator '/' (requires hyphen '-')",
        },
        {
            "input": "15-08-1899",
            "expected": False,
            "desc": "Year 1899 outside 1900-2099 century range",
        },
    ],
    "url": [
        # Positives
        {
            "input": "https://www.example.com",
            "expected": True,
            "desc": "Standard HTTPS domain URL",
        },
        {
            "input": "http://sub.domain.org/path/to/page?query=1&flag=true",
            "expected": True,
            "desc": "HTTP URL with query parameters",
        },
        {
            "input": "https://ugc.gov.in/notices/doc.pdf",
            "expected": True,
            "desc": "HTTPS URL pointing to PDF resource",
        },
        {
            "input": "https://github.com/SHREYAS-M986/TOC_Project#readme",
            "expected": True,
            "desc": "HTTPS URL with section anchor hash",
        },
        {
            "input": "https://dev.to/t/python/page/2",
            "expected": True,
            "desc": "HTTPS URL with pagination path",
        },
        # Negatives
        {
            "input": "ftp://files.example.com",
            "expected": False,
            "desc": "Unsupported FTP protocol (only http/https)",
        },
        {
            "input": "www.example.com",
            "expected": False,
            "desc": "Missing protocol scheme (no http:// or https://)",
        },
        {
            "input": "just text without protocol",
            "expected": False,
            "desc": "Normal prose text",
        },
        {
            "input": "https://",
            "expected": False,
            "desc": "Incomplete protocol without host or path",
        },
        {
            "input": "http://",
            "expected": False,
            "desc": "Incomplete HTTP scheme without host",
        },
    ],
    "hashtag": [
        # Positives
        {"input": "#TOC", "expected": True, "desc": "Uppercase acronym hashtag"},
        {
            "input": "#theory_of_computation",
            "expected": True,
            "desc": "Lowercase hashtag with underscores",
        },
        {
            "input": "#Python3",
            "expected": True,
            "desc": "Alphanumeric hashtag starting with letter",
        },
        {
            "input": "#WebDev_2026",
            "expected": True,
            "desc": "Mixed case hashtag with numbers and underscore",
        },
        {
            "input": "#ComputerScience",
            "expected": True,
            "desc": "CamelCase community hashtag",
        },
        # Negatives
        {
            "input": "#123",
            "expected": False,
            "desc": "Starts with digit (must start with letter)",
        },
        {
            "input": "#_underscore",
            "expected": False,
            "desc": "Starts with underscore (must start with letter)",
        },
        {
            "input": "word#inline",
            "expected": False,
            "desc": "Preceded by word character (fragment anchor)",
        },
        {
            "input": "#",
            "expected": False,
            "desc": "Standalone hash symbol without tag body",
        },
        {"input": "##doublehash", "expected": False, "desc": "Double hash prefix"},
    ],
    "time": [
        # Positives
        {"input": "00:00", "expected": True, "desc": "Midnight 24-hour boundary"},
        {"input": "09:30", "expected": True, "desc": "Morning time with leading zero"},
        {
            "input": "14:45",
            "expected": True,
            "desc": "Afternoon time in 24-hour format",
        },
        {"input": "23:59", "expected": True, "desc": "End of day 23:59 boundary"},
        {"input": "12:00", "expected": True, "desc": "Noon 12:00 time"},
        # Negatives
        {
            "input": "24:00",
            "expected": False,
            "desc": "Invalid hour 24 (24-hour range is 00-23)",
        },
        {"input": "25:10", "expected": False, "desc": "Invalid hour 25"},
        {
            "input": "12:60",
            "expected": False,
            "desc": "Invalid minute 60 (minute range is 00-59)",
        },
        {
            "input": "9:30",
            "expected": False,
            "desc": "Missing leading zero in HH:MM format",
        },
        {"input": "14:5", "expected": False, "desc": "Missing second minute digit"},
    ],
    "ing_word": [
        # Positives
        {
            "input": "programming",
            "expected": True,
            "desc": "Common lowercase participle ending in -ing",
        },
        {
            "input": "Engineering",
            "expected": True,
            "desc": "Capitalized word ending in -ing",
        },
        {"input": "running", "expected": True, "desc": "Verb gerund ending in -ing"},
        {"input": "testing", "expected": True, "desc": "Action word ending in -ing"},
        {
            "input": "PARSING",
            "expected": True,
            "desc": "All uppercase word ending in -ING (case-insensitive)",
        },
        # Negatives
        {
            "input": "ing",
            "expected": False,
            "desc": "Suffix alone with 0 preceding letters",
        },
        {
            "input": "ingenuity",
            "expected": False,
            "desc": "Word starting with 'ing' but not ending in 'ing'",
        },
        {
            "input": "123ing",
            "expected": False,
            "desc": "Preceded by digits instead of alphabetic letters",
        },
        {
            "input": "program-ing",
            "expected": False,
            "desc": "Hyphen before 'ing' breaks word constraint",
        },
        {
            "input": "ring123",
            "expected": False,
            "desc": "Followed by digits (not word boundary)",
        },
    ],
}
