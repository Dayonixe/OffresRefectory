from datetime import datetime
import base64
import requests
from requests.exceptions import RequestException

from .parser import (
    parse_offer_dates,
    extract_code,
    extract_discount,
    extract_cities,
    extract_min_amount,
    KNOWN_CITIES,
)


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
    current_offer: list[str] = []

    for line in lines[idx + 1:]:
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

    results: list[dict] = []

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


def send_ntfy(topic: str, title: str, message: str, priority: int = 3, retries: int = 3, timeout: int = 10) -> bool:
    """
    Sends a notification to an NTFY channel, with retries and error handling.

    This function sends an HTTP POST request to the ntfy.sh server to display
    a notification on a given topic. It will retry a few times in case of
    network / SSL errors and will NOT raise, but return False if all attempts fail.

    :param topic: The name of the topic ntfy (e.g. 'prawse-refectory-alerts-lyon')
    :param title: The title displayed in the notification
    :param message: The textual content of the notification
    :param priority: Notification priority (level 1 to 5). Default: 3
    :param retries: Number of attempts in case of network error. Default: 3
    :param timeout: HTTP request timeout in seconds. Default: 10

    :return: True if the notification was sent successfully, False otherwise
    """
    url = f"https://ntfy.sh/{topic}"

    # Encode title in Base64 to safely support emojis in HTTP headers
    title_b64 = base64.b64encode(title.encode("utf-8")).decode("utf-8")

    headers = {
        "Title": f"=?utf-8?b?{title_b64}?=",
        "Priority": str(priority),
        "Tags": "tada",
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                url,
                data=message.encode("utf-8"),
                headers=headers,
                timeout=timeout,
            )
            if 200 <= resp.status_code < 300:
                return True
            else:
                print(
                    f"⚠️ ntfy {topic}: HTTP {resp.status_code} "
                    f"(attempt {attempt}/{retries})"
                )
        except RequestException as e:
            print(
                f"⚠️ ntfy error to {topic} (attempt {attempt}/{retries}): {e}"
            )

    print(f"❌ Failed to send ntfy notification to {topic} after {retries} attempts.")
    return False


def filter_and_notify(offers: list[dict]) -> None:
    """
    Filters valid offers and sends a ntfy notification per relevant topic.

    Behaviour:
    - Only notifies offers where 'encore_valide' is True.
    - If offer['villes'] == ['Global']:
        -> sends to 'prawse-refectory-alerts'
        -> and to 'prawse-refectory-alerts-{ville}' for ALL KNOWN_CITIES
    - Otherwise:
        -> sends to 'prawse-refectory-alerts'
        -> and to 'prawse-refectory-alerts-{ville}' for each city in offer['villes']

    :param offers: List of structured offers from analyze_offers()
    """
    for offer in offers:
        if not offer["encore_valide"]:
            continue

        print("")

        villes = offer["villes"]

        # Determining destinations
        if villes == ["Global"]:
            topics = [
                "prawse-refectory-alerts",
                *[f"prawse-refectory-alerts-{v.lower()}" for v in KNOWN_CITIES],
            ]
        else:
            topics = [
                "prawse-refectory-alerts",
                *[f"prawse-refectory-alerts-{v.lower()}" for v in villes],
            ]

        # Preparation of notification content
        titre = "Nouvelle offre Refectory !"

        if offer["date_fin"]:
            date_fin_str = offer["date_fin"].strftime("%d/%m")
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
            ok = send_ntfy(topic, titre, message)
            if ok:
                print(f"✅ Notification sent → {topic}")
            else:
                print(f"❌ Notification failed → {topic}")