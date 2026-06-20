"""Tests for merchant normalization + matching."""

from src.merchant import (
    looks_like_offer_credit,
    merchant_match,
    normalize_descriptor,
)


def test_normalize_strips_processor_prefix_and_noise():
    assert normalize_descriptor("SQ *BLUE BOTTLE 8001234 CA") == "blue bottle"
    assert normalize_descriptor("TST* SWEETGREEN - MIDTOWN NY") == "sweetgreen midtown"
    assert normalize_descriptor("STARBUCKS #1102 BUFFALO NY") == "starbucks buffalo"
    assert normalize_descriptor("NIKE #221 PORTLAND OR") == "nike portland"


def test_normalize_handles_paypal_variants():
    assert normalize_descriptor("PP*SPOTIFY") == "spotify"
    assert normalize_descriptor("PAYPAL *SPOTIFY USA") == "spotify"


def test_match_same_merchant_across_noise():
    assert merchant_match("SQ *BLUE BOTTLE 8001234 CA", "Blue Bottle Coffee")
    assert merchant_match("TST* SWEETGREEN - MIDTOWN NY", "Sweetgreen")


def test_match_rejects_different_merchants():
    assert not merchant_match("STARBUCKS #1102 BUFFALO NY", "Blue Bottle Coffee")
    assert not merchant_match("NIKE #221 PORTLAND OR", "Sweetgreen")


def test_offer_credit_detection():
    assert looks_like_offer_credit("Amex Offer Credit - Blue Bottle")
    assert looks_like_offer_credit("CHASE OFFER CASH BACK")
    assert not looks_like_offer_credit("BLUE BOTTLE COFFEE PURCHASE")
