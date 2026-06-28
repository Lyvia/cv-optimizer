"""
test_anonymizer.py — Checks what the anonymizer detects and replaces.
Run with: python test_anonymizer.py

You can replace the CV_SAMPLE block below with your own text to test.
"""

import sys
import os

# Allows running the script from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.anonymizer import anonymize

# ─── Sample CV ────────────────────────────────────────────────────────────────
# Replace this block with your own text to test

CV_SAMPLE = """
John Doe
john.doe@gmail.com | +1 555 123 4567
linkedin.com/in/john-doe | github.com/johndoe
123 Main Street, 75011 Paris
https://johndoe.dev

PROFESSIONAL EXPERIENCE

Digital Project Manager — Acme Corp (2021-2024)
- Managed a team of 8 people
- Increased conversion rate by 32%

EDUCATION

Master in Management — HEC Paris (2019)

SKILLS
Python, SQL, Figma, Jira
"""

# ─── Test ─────────────────────────────────────────────────────────────────────

def run_test(text: str):
    print("=" * 60)
    print("ORIGINAL TEXT")
    print("=" * 60)
    print(text)

    result = anonymize(text)

    print("\n" + "=" * 60)
    print("ANONYMIZED TEXT (sent to the AI)")
    print("=" * 60)
    print(result.anonymized_text)

    print("\n" + "=" * 60)
    print(f"REPLACED ELEMENTS ({len(result.summary)})")
    print("=" * 60)
    if result.summary:
        for item in result.summary:
            print(f"  • {item}")
    else:
        print("  No element detected.")

    print("\n" + "=" * 60)
    print("MAPPING TABLE (placeholders → real values)")
    print("=" * 60)
    if result.replacements:
        for placeholder, original in result.replacements.items():
            print(f"  {placeholder:30s} → {original}")
    else:
        print("  Empty.")

    print("\n" + "=" * 60)
    print("QUICK CHECK")
    print("=" * 60)
    # Check that originals are gone from anonymized text
    all_ok = True
    for placeholder, original in result.replacements.items():
        if original in result.anonymized_text:
            print(f"  ❌ '{original}' is still present in the anonymized text!")
            all_ok = False
    if all_ok and result.replacements:
        print("  ✅ All sensitive values were replaced.")
    elif not result.replacements:
        print("  ⚠️  Nothing was replaced — check that the text contains personal data.")


# ─── Automated regression tests (pytest test_anonymizer.py -v) ────────────────

def test_iso_standard_number_not_redacted_as_postal_code():
    """CVO-11: "ISO 27001" must not be wrongly treated as a postal code."""
    result = anonymize("ISO 27001 certified company")
    assert "ISO 27001" in result.anonymized_text
    assert not any("27001" in v for v in result.replacements.values())


def test_other_iso_standard_numbers_not_redacted():
    result = anonymize("Certified ISO 14001 and ISO 9001:2015")
    assert "ISO 14001" in result.anonymized_text
    assert "ISO 9001" in result.anonymized_text


def test_real_postal_code_with_city_still_redacted():
    """Postal code + city (the documented, intended case) must still be caught."""
    result = anonymize("123 Main Street, 75011 Paris")
    assert "75011 Paris" not in result.anonymized_text
    assert any("75011 Paris" in v for v in result.replacements.values())


def test_bare_five_digit_number_without_city_not_redacted():
    """A standalone 5-digit number with nothing capitalized after it is not
    a postal code on its own (module docstring: "city + zip code")."""
    result = anonymize("Budget: 75011 dollars allocated")
    assert "75011" in result.anonymized_text


if __name__ == "__main__":
    # If a file is passed as an argument, use it
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            sys.exit(1)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        print(f"Testing file: {filepath}\n")
    else:
        text = CV_SAMPLE
        print("Testing the sample CV (edit CV_SAMPLE in this script to test your own)\n")

    run_test(text)
