import re
import unicodedata
from typing import Union
from functools import lru_cache
from .utils import is_domain_valid, is_disposable
from .schemas import EmailResponse
from .exceptions_types import EmailFormatError, DisposableEmailError, EmailMXRecordError


class EmailValidator:
    DISPOSABLE_CACHE = {}
    MX_CACHE = {}

    def __init__(self, email: Union[str, bytes], **options):
        if isinstance(email, bytes):
            try:
                email = email.decode("ascii")
            except ValueError as e:
                raise EmailFormatError("The email address is not valid ASCII.") from e

        self.email = email
        self.options = {
            "allow_smtputf8": False,
            "allow_empty_local": False,
            "allow_quoted_local": False,
            "allow_domain_literal": False,
            "allow_display_name": False,
            "check_deliverability": True,
            "test_environment": False,
            "globally_deliverable": True,
            "timeout": 10,
            **options,
        }
        self.local_part, self.domain, self.display_name, self.is_quoted_local = (
            self._split_email()
        )

    def _split_email(self):
        """Split the email into display name, local part, and domain, handling quoted local parts."""
        match = re.match(r'(?:\"?([^@"]+)\"?\s)?<(.+)>|(.+)', self.email)
        if not match:
            raise EmailFormatError("Invalid email format.")

        display_name, addr_spec, fallback = match.groups()
        local_part, domain = (addr_spec or fallback).split("@", 1)

        # Check for quoted local part if allowed
        is_quoted_local = local_part.startswith('"') and local_part.endswith('"')
        if is_quoted_local:
            if self.options["allow_quoted_local"] is not True:
                raise EmailFormatError("Quoted local part is not allowed.")
            local_part = local_part.strip('"')

        local_part = unicodedata.normalize("NFC", local_part)
        domain = unicodedata.normalize("NFC", domain)

        return local_part, domain, display_name, is_quoted_local

    def _check_email_pattern(self, email: str) -> bool:
        """Check if the email matches the correct pattern using regex."""
        pattern = (
            r"^(?:(?:\"[^\"]*\")|(?:[a-zA-Z0-9._%+-]+))@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )
        valid = bool(re.match(pattern, email.strip()))
        return valid

    @lru_cache(maxsize=1024)
    def _is_disposable_cached(self, domain: str) -> bool:
        """Cached check for disposable domains."""
        if domain in self.DISPOSABLE_CACHE:
            return self.DISPOSABLE_CACHE[domain]
        result = is_disposable(domain)
        self.DISPOSABLE_CACHE[domain] = result
        return result

    @lru_cache(maxsize=1024)
    def _is_mx_valid_cached(self, domain: str) -> bool:
        """Cached check for MX record validity."""
        if domain in self.MX_CACHE:
            return self.MX_CACHE[domain]
        result = is_domain_valid(domain)
        self.MX_CACHE[domain] = result
        return result

    def validate(self) -> EmailResponse:
        """Main validation entry point."""

        # Disposable email check
        if self._is_disposable_cached(self.domain):
            raise DisposableEmailError("Disposable email addresses are not allowed.")

        if not self._check_email_pattern(self.email):
            raise EmailFormatError("Invalid email format.")

        # Domain literal check
        if self.domain.startswith("[") and self.domain.endswith("]"):
            if not self.options["allow_domain_literal"]:
                raise EmailFormatError("Domain literal is not allowed.")

        # MX Record check if deliverability checks are enabled
        if (
            self.options["check_deliverability"]
            and not self.options["test_environment"]
        ):
            if not self._is_mx_valid_cached(self.domain):
                raise EmailMXRecordError("Domain has no valid MX records.")

        # Return validated email
        return EmailResponse(email=self.email, is_valid=True, message="Email is valid.")

    def check_disposable(self) -> EmailResponse:
        """Check if the email domain is disposable."""
        disposable = self._is_disposable_cached(self.domain)
        message = "Domain is disposable." if disposable else "Domain is not disposable."
        return EmailResponse(
            email=self.email,
            is_valid=not disposable,
            message=message,
        )

    def check_mx_record(self) -> EmailResponse:
        """Check if the email domain has valid MX records."""
        has_mx = self._is_mx_valid_cached(self.domain)
        message = "Valid MX records found." if has_mx else "No valid MX records."
        return EmailResponse(
            email=self.email,
            is_valid=has_mx,
            message=message,
        )

    def is_globally_deliverable(self) -> bool:
        """Determine if the domain is globally deliverable, considering restricted TLDs."""
        if not self.options.get("globally_deliverable", False):
            return True

        restricted_tlds = {"local", "example", "invalid", "test"}
        tld = self.domain.split(".")[-1].lower()
        if tld in restricted_tlds:
            return False

        result = self._is_mx_valid_cached(self.domain)
        return result
