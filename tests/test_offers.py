import pytest
from src.parser import (
    parse_french_date,
    parse_offer_dates,
    extract_code,
    extract_discount,
    extract_cities,
    extract_min_amount,
    analyze_offers
)



################################
#  parse_french_date           #
################################

@pytest.mark.parametrize("day,month,expected_month", [
    ("1", "janvier", 1),
    ("12", "février", 2),
    ("30", "mars", 3),
    ("7", "novembre", 11),
])
def test_parse_french_date(day, month, expected_month):
    d = parse_french_date(day, month)
    assert d.day == int(day)
    assert d.month == expected_month



################################
#  parse_offer_dates           #
################################

@pytest.mark.parametrize("text,start_day,end_day,start_month,end_month", [
    ("Du 1 au 5 janvier", 1, 5, 1, 1),
    ("Du 18/11 au 21/11", 18, 21, 11, 11),
    ("Du 3 au 12 août", 3, 12, 8, 8),
    ("Du 10/02 au 15/02", 10, 15, 2, 2),
])
def test_parse_offer_dates_valid(text, start_day, end_day, start_month, end_month):
    start, end = parse_offer_dates(text)
    assert start.day == start_day
    assert end.day == end_day
    assert start.month == start_month
    assert end.month == end_month


def test_parse_offer_dates_invalid():
    s, e = parse_offer_dates("Pas une date du tout")
    assert s is None and e is None



################################
#  extract_code                #
################################

@pytest.mark.parametrize("text,expected", [
    ("Code promo TESTCODE à utiliser", "TESTCODE"),
    ("1€ offert avec le code ABCDEF", "ABCDEF"),
    ("aucun code ici", None),
    ("Utilisez le code SUPERMEGA123", "SUPERMEGA123"),
])
def test_extract_code(text, expected):
    assert extract_code(text) == expected



################################
#  extract_discount            #
################################

@pytest.mark.parametrize("text,expected", [
    ("Profitez de 1€ offert", "1€"),
    ("Réduction de 2 € immédiate", "2€"),
    ("Seulement 10€ de minimum", "10€"),
    ("pas de remise", None),
])
def test_extract_discount(text, expected):
    assert extract_discount(text) == expected



################################
#  extract_cities              #
################################

@pytest.mark.parametrize("text,expected", [
    ("Offre valable à Toulouse uniquement", ["Toulouse"]),
    ("Uniquement à Paris et Lyon", ["Paris", "Lyon"]),
    ("Offre nationale sans ville", ["Général"]),
])
def test_extract_cities_multiple(text, expected):
    assert extract_cities(text) == expected



################################
#  extract_min_amount          #
################################

@pytest.mark.parametrize("text,expected", [
    ("Valable pour un montant minimum de 7€90", "7€90"),
    ("minimum de 10€ requis", "10€"),
    ("à partir d'un montant minimum de 12,50€", "12,50€"),
    ("aucune condition de montant", None),
])
def test_extract_min_amount(text, expected):
    assert extract_min_amount(text) == expected



################################
#  analyze_offers              #
################################

def test_analyze_offers_complex():
    TEXT = """
Offres en cours
Du 10/11 au 12/11
1€ offert avec le code ABC123.
Offre valable à Paris et Toulouse.
montant minimum de 7€90.

Du 1 au 5 décembre
Pour toute commande, utilisez le code MEGA.
Uniquement à Lyon.
minimum de 12€.

Offres de bienvenue
"""
    results = analyze_offers(TEXT)

    assert len(results) == 2

    o1 = results[0]
    assert o1["code_promo"] == "ABC123"
    assert o1["remise"] == "1€"
    assert sorted(o1["villes"]) == ["Paris", "Toulouse"]

    o2 = results[1]
    assert o2["code_promo"] == "MEGA"
    assert o2["villes"] == ["Lyon"]
    assert o2["montant_minimum"] == "12€"


def test_analyze_offers_missing_section():
    TEXT = "Aucune offre ici"
    assert analyze_offers(TEXT) == []
