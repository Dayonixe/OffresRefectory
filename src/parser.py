import re
from datetime import datetime

# Liste des villes connues Refectory
KNOWN_CITIES = [
    "Avelin", "Bordeaux", "Caen", "Clermont", "Grenoble", "Lille", "Limonest",
    "Lyon", "Marseille", "Metz", "Montpellier", "Nancy", "Nantes", "Nice",
    "Paris", "Rennes", "Rouen", "Strasbourg", "Toulouse"
]

MONTHS_FR = {
    "janvier":1, "février":2, "mars":3, "avril":4, "mai":5, "juin":6,
    "juillet":7, "août":8, "septembre":9, "octobre":10, "novembre":11, "décembre":12
}

def parse_french_date(day, month_text):
    """Transforme '17' + 'novembre' en datetime."""
    month = MONTHS_FR[month_text.lower()]
    year = datetime.now().year
    return datetime(year, month, int(day))

def parse_offer_dates(text):
    """
    Détecte les dates dans 'Du 17 au 21 novembre' ou 'Du 18/11 au 21/11'
    Renvoie (start_date, end_date) en datetime.
    """

    # Format "Du 17 au 21 novembre"
    m1 = re.search(r"Du\s+(\d{1,2})\s+au\s+(\d{1,2})\s+([a-zA-Zéû]+)", text)
    if m1:
        d1, d2, month = m1.groups()
        return parse_french_date(d1, month), parse_french_date(d2, month)

    # Format "Du 18/11 au 21/11"
    m2 = re.search(r"Du\s+(\d{1,2})/(\d{1,2})\s+au\s+(\d{1,2})/(\d{1,2})", text)
    if m2:
        d1, m1, d2, m2 = m2.groups()
        year = datetime.now().year
        return (
            datetime(year, int(m1), int(d1)),
            datetime(year, int(m2), int(d2)),
        )

    return None, None

def extract_code(text):
    m = re.search(r"\b([A-Z0-9]{4,})\b", text)
    return m.group(1) if m else None

def extract_discount(text):
    m = re.search(r"(\d+[.,]?\d*)\s*€", text)
    if m:
        amount = m.group(1).replace(",", ".")
        return amount.replace(".", ",") + "€"
    return None

def extract_cities(text):
    pattern = r"\b(" + "|".join(KNOWN_CITIES) + r")\b"
    matches = re.finditer(pattern, text, flags=re.I)
    cities = [m.group(1) for m in matches]
    return cities if cities else ["Général"]

def extract_min_amount(text):
    # Capture 7€90 | 12,50€ | 10€ | 9.90 | 12,50 | 10
    m = re.search(r"minimum[^0-9]*([0-9]+(?:[€.,][0-9]{1,2})?)", text, flags=re.I)
    if not m:
        return None

    amount = m.group(1)

    # ---- Cas 1 : format 7€90 → OK ----
    if "€" in amount and re.search(r"\d€\d{1,2}", amount):
        return amount

    # ---- Cas 2 : format 12,50 | 12.50 ----
    if "," in amount or "." in amount:
        # Normaliser en virgule
        amount = amount.replace(".", ",")
        if not amount.endswith("€"):
            amount += "€"
        return amount

    # ---- Cas 3 : format 10€ ou 10 ----
    if amount.isdigit():
        amount += "€"

    return amount

def analyze_offers(full_text):
    lines = full_text.split("\n")

    # On localise la section "Offres en cours"
    try:
        idx = lines.index("Offres en cours")
    except ValueError:
        print("Aucune section 'Offres en cours' trouvée.")
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