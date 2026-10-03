"""Canonical identity rules for catalog assets."""


def normalize_ticker(ticker: str) -> str:
    """Return the identity form used by new catalog records and lookups."""
    return ticker.strip().upper()
