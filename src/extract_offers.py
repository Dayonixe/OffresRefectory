from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from .parser import analyze_offers

URL = "https://www.refectory.fr/conditions-des-offres-en-cours"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("🔍 Loading page...")
        page.goto(URL, wait_until="networkidle")

        # 1) Accepter les cookies si la bannière apparaît
        try:
            page.locator("text=Tout accepter").first.click(timeout=2000)
            print("✅ Cookies accepted")
        except:
            print("🔍 No cookie banner detected")

        # 2) Attendre que le vrai contenu ('Offres en cours') soit visible
        print("🔍 Waiting for content to load...")
        page.wait_for_selector("h2", timeout=10000)

        # 3) Récupérer le HTML final
        html = page.content()
        browser.close()

    # Extraction via BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Trouver la section contenant les offres
    offers_block = soup.find("h2", string=lambda t: t and "Offres" in t)
    if not offers_block:
        print("❌ Unable to find offers on the page!")
        return

    container = offers_block.find_parent()  # remonte au bloc
    text = container.get_text("\n", strip=True)

    offers = analyze_offers(text)

    for o in offers:
        print("\n--- OFFER ---")
        for k, v in o.items():
            print(f"{k}: {v}")

if __name__ == "__main__":
    main()
