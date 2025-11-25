import re
from datetime import datetime

# List of well-known cities Refectory
KNOWN_CITIES = [
    "Avelin", "Bordeaux", "Caen", "Clermont", "Grenoble", "Lille", "Limonest",
    "Lyon", "Marseille", "Metz", "Montpellier", "Nancy", "Nantes", "Nice",
    "Paris", "Rennes", "Rouen", "Strasbourg", "Toulouse"
]

MONTHS_FR = {
    "janvier":1, "février":2, "mars":3, "avril":4, "mai":5, "juin":6,
    "juillet":7, "août":8, "septembre":9, "octobre":10, "novembre":11, "décembre":12
}


def parse_french_date(day: str, month_text: str) -> datetime:
    """
    Converts a French date in text form into a Python datetime object.

    :param day: Day of the month (numeric format, e.g. '17')
    :param month_text: The month in full in French (e.g. 'novembre')

    :return: A datetime object corresponding to the date (current year)
    """
    month = MONTHS_FR[month_text.lower()]
    year = datetime.now().year
    return datetime(year, month, int(day))


def parse_offer_dates(text: str) -> tuple[datetime | None, datetime | None]:
    """
    Extracts the validity period of an offer from a text.

    :param text: The text, which may contain an offer period

    :return: A tuple (start_date, end_date) in datetime format or (None, None) if no valid format is detected
    """

    # "Du 17 au 21 novembre" format
    m1 = re.search(r"Du\s+(\d{1,2})\s+au\s+(\d{1,2})\s+([a-zA-Zéû]+)", text)
    if m1:
        d1, d2, month = m1.groups()
        return parse_french_date(d1, month), parse_french_date(d2, month)

    # "Du 18/11 au 21/11" format
    m2 = re.search(r"Du\s+(\d{1,2})/(\d{1,2})\s+au\s+(\d{1,2})/(\d{1,2})", text)
    if m2:
        d1, m1, d2, m2 = m2.groups()
        year = datetime.now().year
        return (
            datetime(year, int(m1), int(d1)),
            datetime(year, int(m2), int(d2)),
        )

    return None, None


def extract_code(text: str) -> str | None:
    """
    Extract a promotional code from the text.

    :param text: The text to be analysed

    :return: The promotional code found or None if none is detected
    """
    m = re.search(r"\b([A-Z0-9]{4,})\b", text)
    return m.group(1) if m else None


def extract_discount(text: str) -> str | None:
    """
    Extract the amount of the discount from a text.

    :param text: The text to be analysed

    :return: A string representing the reduction (e.g. '1€') or None if no value is found
    """
    m = re.search(r"(\d+[.,]?\d*)\s*€", text)
    if m:
        amount = m.group(1).replace(",", ".")
        return amount.replace(".", ",") + "€"
    return None


def extract_cities(text: str) -> list[str]:
    """
    Extract the city or cities concerned by an offer.

    Compare the text with a list of well-known cities Refectory.
    The cities are extracted in the order in which they appear in the text.

    :param text: The text to be analysed

    :return: A list of detected cities or ['Global'] if none appear
    """
    pattern = r"\b(" + "|".join(KNOWN_CITIES) + r")\b"
    matches = re.finditer(pattern, text, flags=re.I)
    cities = [m.group(1) for m in matches]
    return cities if cities else ["Global"]


def extract_min_amount(text: str) -> str | None:
    """
    Extract the minimum amount required in an offer.

    :param text: The text containing any information regarding the amount

    :return: The minimum formatted amount or None if not detected
    """
    # Capture 7€90 | 12,50€ | 10€ | 9.90 | 12,50 | 10
    m = re.search(r"minimum[^0-9]*([0-9]+(?:[€.,][0-9]{1,2})?)", text, flags=re.I)
    if not m:
        return None

    amount = m.group(1)

    # 7€90 format
    if "€" in amount and re.search(r"\d€\d{1,2}", amount):
        return amount

    # 12,50 | 12.50 format
    if "," in amount or "." in amount:
        amount = amount.replace(".", ",")  # Normalise to decimal point
        if not amount.endswith("€"):
            amount += "€"
        return amount

    # 10€ | 10 format
    if amount.isdigit():
        amount += "€"

    return amount


def analyze_offers(full_text: str) -> list[dict]:
    """
    Analyses the 'Offres en cours' section and extracts each offer in a structured format.

    For each offer, the function:
    - extracts the period (start/end)
    - determines whether the offer is still valid
    - detects the promo code
    - extracts any discount
    - detects the cities concerned
    - extracts the minimum amount
    - returns the original plain text

    :param full_text: The full text containing all sections of the offers

    :return: A list of dictionaries representing each offer analysed
    """
    lines = full_text.split("\n")

    # Locate the 'Offres en cours' section
    try:
        idx = lines.index("Offres en cours")
    except ValueError:
        print("❌ No 'Offres en cours' section found!")
        return []

    offers = []
    current_offer = []

    for line in lines[idx+1:]:
        if line.startswith("Offres de bienvenue") or line.startswith("Parrainage"):
            break

        if line.startswith("Du "):
            if current_offer:
                offers.append("\n".join(current_offer))
            current_offer = [line]
        else:
            current_offer.append(line)

    if current_offer:
        offers.append("\n".join(current_offer))

    results = []

    for offer in offers:
        start, end = parse_offer_dates(offer)
        code = extract_code(offer)
        discount = extract_discount(offer)
        cities = extract_cities(offer)
        min_amount = extract_min_amount(offer)

        validity = None
        if start and end:
            now = datetime.now()
            validity = start <= now <= end

        results.append({
            "texte_original": offer,
            "date_debut": start,
            "date_fin": end,
            "encore_valide": validity,
            "code_promo": code,
            "remise": discount,
            "villes": cities,
            "montant_minimum": min_amount,
        })

    return results