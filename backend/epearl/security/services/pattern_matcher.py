import re

# Pre‑compile regular expressions for common attack patterns
SQL_INJECTION_PATTERNS = [
    re.compile(r"(\bSELECT\b.*\bFROM\b)", re.IGNORECASE),
    re.compile(r"(\bINSERT\b.*\bINTO\b)", re.IGNORECASE),
    re.compile(r"(\bUPDATE\b.*\bSET\b)", re.IGNORECASE),
    re.compile(r"(\bDELETE\b.*\bFROM\b)", re.IGNORECASE),
    re.compile(r"(\bDROP\b.*\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bUNION\b.*\bSELECT\b)", re.IGNORECASE),
    re.compile(r"('|;|\bOR\b|\bAND\b)\s*('.*'|\d+)", re.IGNORECASE),
]

XSS_PATTERNS = [
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"onerror\s*=", re.IGNORECASE),
    re.compile(r"onload\s*=", re.IGNORECASE),
    re.compile(r"alert\s*\(", re.IGNORECASE),
    re.compile(r"<img[^>]+src\s*=\s*['\"]?javascript:", re.IGNORECASE),
]

PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.\\"),
    re.compile(r"\.\.%2f", re.IGNORECASE),
    re.compile(r"\.\.%5c", re.IGNORECASE),
    re.compile(r"\.\.%252f", re.IGNORECASE),
]


class PatternMatcher:
    @classmethod
    def contains_sql_injection(cls, text):
        if not text:
            return False
        for pattern in SQL_INJECTION_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @classmethod
    def contains_xss(cls, text):
        if not text:
            return False
        for pattern in XSS_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @classmethod
    def contains_path_traversal(cls, text):
        if not text:
            return False
        for pattern in PATH_TRAVERSAL_PATTERNS:
            if pattern.search(text):
                return True
        return False