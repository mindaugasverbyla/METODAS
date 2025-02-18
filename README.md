# METODAS
Baigiamasis PYTHON mokymų darbas.

Autorius: Mindaugas Verbyla
El. paštas: mindaugas@verbyla.lt

Programa naaudoja daugiakriterionio kompleksnio įvertinimo metodą. Pagal mūsų užsiduotus kriterijus yra vertinami objektai. Informacija apie objektus traukiama iš interneto svetainės (naudojama 'BeautifulSoap' biblioteka)

Pradžioje reikia prisiregistruoti sistemoje. Jūsų prisiregistravimo duomenys bus atsiųsti Jums paštu (naudota 'Gmail API', slaptažodžio šifravimas 'su bcrypt', duomenų bazės su 'sqlite3')

PROJEKTAI - suvedame sau aktualius projektus. Įvedame projekto pavadinimą, nuorodą, iš kurios bus traukiami mūsų objektų duomenys, bei skripto, kuris nuskaitys svetainę, pavadinimas. Iki 2025-02-14 yra realizuoti 3 skriptai: 'domoplius-2025-02-14', 'brc-2025-02-14', 'tele2-2025-02-14'

KRITERIJAI - suvedame sau aktualius kriterijus. Įvedame kriterijaus pavadinimą, kriterijaus reikšmę (taip apibrėžiamas kriterijaus svoris), pasirenkama kriterijaus įtaka galutiniam rezultatui (galimi pasirinkimai: 'Teigiamas' ir 'Neigiamas'), įvedami matavimo vienetai, įvedamas kriterijaus tipas (jei reikšmės importuojamos 'Auto', jei suvedamos 'Įvedamas') bei nurodoma reikšmės pozicija iš svetainės nuskaitymo skripto sugeneruotų duomenų.

OBJEKTAI - tai objektai, kuriuos išsitraukiame iš svetainės, naudodami svetainės nuskaitymo skriptą. Čia įvedame laukelius, jei pažymėti kaip 'Įvedamas', pataisome reikšmes, jei jos blogai ištrauktos iš svetainės, pasirenkame tuos objektus, kurie mus domina (iš 'Nepasirinktas' keičiame į 'Pasirinktas').

REZUTATAI - po daugiakriterinių kompleksinių skaičiavimų pateikiamas objektų sąrašas pagal prioritetą.
