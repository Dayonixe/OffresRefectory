from datetime import datetime
import requests
from .parser import (
    parse_offer_dates,
    extract_code,
    extract_discount,
    extract_cities,
    extract_min_amount
)
from .parser import KNOWN_CITIES


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


def send_ntfy(topic: str, title: str, message: str, priority: int = 3) -> None:
    """
    Sends a notification to an NTFY channel.

    This function sends an HTTP POST request to the ntfy.sh server to display a notification on a given topic.

    :param topic: The name of the topic ntfy
    :param title: The title displayed in the notification
    :param message: The textual content of the notification
    :param priority: Notification priority (level 1 to 5)
                     Default: 3
                     Reference: https://docs.ntfy.sh/publish/#message-priority
    """
    url = f"https://ntfy.sh/{topic}"
    headers = {
        "Title": title,
        "Priority": str(priority),
        "Tags": "tada"
    }
    requests.post(url, data=message.encode("utf-8"), headers=headers)


def filter_and_notify(offers: list[dict]) -> None:
    """
    Filters valid and relevant offers, then sends a ntfy notification.

    :param offers: List of structured offers from analyze_offers()
    """
    for offer in offers:
        if not offer["encore_valide"]:
            continue

        print("")

        villes = offer["villes"]

        # Determining destinations
        if villes == ["Global"]:
            topics = (
                [f"prawse-refectory-alerts"] +
                [f"prawse-refectory-alerts-{v.lower()}" for v in KNOWN_CITIES]
            )
        else:
            topics = (
                ["prawse-refectory-alerts"] +
                [f"prawse-refectory-alerts-{v.lower()}" for v in villes]
            )

        # Preparation of notification content
        titre = "Nouvelle offre Refectory !"

        if offer["date_fin"]:
            date_fin_str = offer["date_fin"].strftime('%d/%m')
        else:
            date_fin_str = "inconnue"

        details = [
            f"Offre valable jusqu’au {date_fin_str}",
            f"Ville(s) : {', '.join(villes)}",
        ]

        if offer["code_promo"]:
            details.append(f"Code promo : {offer['code_promo']}")

        if offer["remise"]:
            details.append(f"Remise : {offer['remise']}")

        if offer["montant_minimum"]:
            details.append(f"Minimum : {offer['montant_minimum']}")

        details.append("")
        details.append("Texte d'origine :")
        details.append(offer["texte_original"])

        message = "\n".join(details)

        # Notification to all topics
        for topic in topics:
            send_ntfy(topic, titre, message)

            print(f"✅ Notification sent → {topic}")
