# User Manual

Team : Théo Pirouelle

<a href="https://www.python.org/">
  <img src="https://img.shields.io/badge/language-python-blue?style=flat-square" alt="laguage-python" />
</a>

![TestsResult](https://github.com/Dayonixe/OffresRefectory/actions/workflows/python-tests.yml/badge.svg)

---

## Installation

> [!NOTE]
> For information, the code has been developed and works with the following library versions:
> | Library | Version |
> | --- | --- |
> | playwright | 1.56.0 |
> | bs4 | 0.0.2 |
> | pytest | 9.0.1 |

Please also remember to install Python. The code was developed and works with Python 3.10.12.

For the complete installation of playwright, you may need to supplement it with the install of playwright.
```bash
# After using 'pip install playwright'
playwright install --with-deps
```

---

## Usage

To run the script in a Linux or PowerShell terminal:
```bash
python[3] -m src.extract_offers
```

The script will run and you should see the following lines displayed, for example:
```
🔍 Loading page...
✅ Cookies accepted
🔍 Waiting for content to load...

--- OFFER ---
texte_original: Du 17 au 21 novembre, pour la commande d'un menu complet (entrée + plat + dessert) on vous offre un fromage individuel : le cantal. Dans la limite des stocks disponibles.
date_debut: 2025-11-17 00:00:00
date_fin: 2025-11-21 00:00:00
encore_valide: False
code_promo: None
remise: None
villes: ['Global']
montant_minimum: None

--- OFFER ---
texte_original: Du 18/11 au 21/11, 1€ de réduction immédiate en indiquant le code TOUCHESUCREE dans votre panier au moment de valider votre commande. L’offre est valable uniquement si votre commande comporte un dessert de la catégorie "desserts de chef" ou "grands classiques" et pour un montant minimum de 7€90 sur www.refectory.fr ou l'application.
Cette offre est valable une fois. Elle n'est ni remboursable, ni échangeable, ni cumulable avec d'autres offres en cours. Dans la limite des stocks disponibles. Uniquement dans le secteur d'Avelin.
date_debut: 2025-11-18 00:00:00
date_fin: 2025-11-21 00:00:00
encore_valide: False
code_promo: TOUCHESUCREE
remise: 1€
villes: ['Avelin']
montant_minimum: 7€90
```