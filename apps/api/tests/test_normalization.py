import pytest
from app.services.normalization import (
    normalize_domain,
    normalize_email,
    split_full_name,
    is_consumer_webmail_domain,
)


class TestDomainNormalization:
    """Rigorous edge-case tests for canonical domain normalization with Public Suffix List."""

    @pytest.mark.parametrize(
        "raw_input,expected",
        [
            # Basic domains
            ("stripe.com", "stripe.com"),
            ("STRIPE.COM", "stripe.com"),
            ("  google.com  ", "google.com"),
            
            # Protocols and schemes
            ("https://linear.app", "linear.app"),
            ("http://linear.app", "linear.app"),
            ("ftp://ftp.acme.org", "acme.org"),
            ("//github.com", "github.com"),
            
            # Subdomains and www
            ("www.datadoghq.com", "datadoghq.com"),
            ("https://www.datadoghq.com", "datadoghq.com"),
            ("blog.hubspot.com", "hubspot.com"),
            ("app.snowflake.com", "snowflake.com"),
            ("portal.service.acme.com", "acme.com"),
            
            # Paths, query params, fragments, and ports
            ("https://acme.com/about-us?utm_source=adwords#team", "acme.com"),
            ("http://acme.com:8080/api/v1", "acme.com"),
            ("https://user:password@secure.acme.com:443/login", "acme.com"),
            
            # Two-part public suffixes (DEF-01 regressions)
            ("bbc.co.uk", "bbc.co.uk"),
            ("www.bbc.co.uk", "bbc.co.uk"),
            ("news.bbc.co.uk", "bbc.co.uk"),
            ("canberra.gov.au", "canberra.gov.au"),
            ("www.company.com.au", "company.com.au"),
            ("tokyo.co.jp", "tokyo.co.jp"),
            ("sub.portal.tokyo.co.jp", "tokyo.co.jp"),
            ("tata.co.in", "tata.co.in"),
            ("itau.com.br", "itau.com.br"),
            ("company.com.sg", "company.com.sg"),
            ("tech.gov.sg", "tech.gov.sg"),
            ("company.co.id", "company.co.id"),        # DEF-01 regression: Indonesia
            ("firm.com.pk", "firm.com.pk"),          # DEF-01 regression: Pakistan
            ("enterprise.co.za", "enterprise.co.za"),  # South Africa
            ("agency.com.ua", "agency.com.ua"),        # Ukraine
            ("business.com.ng", "business.com.ng"),    # Nigeria
            ("software.com.pl", "software.com.pl"),    # Poland
            
            # Email input
            ("john.doe@salesforce.com", "salesforce.com"),
            ("contact@uk.enterprise.co.uk", "enterprise.co.uk"),
            ("founder@company.co.id", "company.co.id"),
            
            # IDN / Punycode
            ("https://münchen.de", "xn--mnchen-3ya.de"),
            
            # Public-suffix-only inputs (must NOT normalize to a registrable domain)
            ("gov.sg", ""),
            ("co.uk", ""),
            ("co.id", ""),
            ("com", ""),
            ("org", ""),
            
            # Invalid / malformed inputs
            ("", ""),
            (None, ""),
            ("    ", ""),
            ("notadomain", ""),
            ("192.168.1.1", ""),
            ("http://localhost:3000", ""),
            ("http://invalid", ""),
        ]
    )
    def test_normalize_domain_cases(self, raw_input, expected):
        assert normalize_domain(raw_input) == expected


class TestConsumerWebmailDetection:
    """Tests for DEF-02: consumer webmail domain detection."""

    @pytest.mark.parametrize(
        "raw_input,expected",
        [
            # Gmail
            ("alice@gmail.com", True),
            ("GMAIL.COM", True),
            ("https://gmail.com", True),
            ("bob@googlemail.com", True),
            
            # Microsoft
            ("lead@outlook.com", True),
            ("user@hotmail.com", True),
            ("test@hotmail.co.uk", True),
            ("contact@live.com", True),
            ("person@msn.com", True),
            
            # Yahoo
            ("sales@yahoo.com", True),
            ("uk_lead@yahoo.co.uk", True),
            ("jp_lead@yahoo.co.jp", True),
            ("old@ymail.com", True),
            
            # Apple & Proton
            ("founder@icloud.com", True),
            ("dev@me.com", True),
            ("privacy@proton.me", True),
            ("secure@protonmail.com", True),
            
            # Corporate / business domains (must NOT be detected as consumer webmail)
            ("alice@stripe.com", False),
            ("bob@datadoghq.com", False),
            ("founder@company.co.id", False),
            ("salesforce.com", False),
            ("https://acme-innovations.com", False),
            ("", False),
            (None, False),
        ]
    )
    def test_consumer_webmail_detection_cases(self, raw_input, expected):
        assert is_consumer_webmail_domain(raw_input) == expected


class TestEmailNormalization:
    """Tests for email normalization and validation."""

    @pytest.mark.parametrize(
        "raw_email,expected",
        [
            ("alice@example.com", "alice@example.com"),
            ("  Bob.Smith@ACME.ORG  ", "bob.smith@acme.org"),
            ("user+tag@domain.co.uk", "user+tag@domain.co.uk"),
            ("valid.name_123@sub.domain.io", "valid.name_123@sub.domain.io"),
            
            # Invalid cases
            ("", ""),
            (None, ""),
            ("plainaddress", ""),
            ("@missinguser.com", ""),
            ("missingdomain@", ""),
            ("user@.com", ""),
            ("user@domain", ""),
        ]
    )
    def test_normalize_email_cases(self, raw_email, expected):
        assert normalize_email(raw_email) == expected


class TestNameSplitting:
    """Tests for full name splitting into first and last name."""

    @pytest.mark.parametrize(
        "raw_name,expected_first,expected_last",
        [
            ("Jane Doe", "Jane", "Doe"),
            ("  Alex   Smith  ", "Alex", "Smith"),
            ("Cher", "Cher", ""),
            ("Dr. Gregory House", "Gregory", "House"),
            ("Mr. John Jacob Jingleheimer Schmidt", "John", "Jacob Jingleheimer Schmidt"),
            ("", "", ""),
            (None, "", ""),
        ]
    )
    def test_split_full_name_cases(self, raw_name, expected_first, expected_last):
        first, last = split_full_name(raw_name)
        assert first == expected_first
        assert last == expected_last
