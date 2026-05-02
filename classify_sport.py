#!/usr/bin/env python3
"""
Classifier de sport pour CSV Winamax.

Le scraper JS ne peut pas détecter le sport (pas affiché sur la page history).
Ce script lit le CSV brut et déduit le sport via :
  1. Pattern selection (joueur "X. Y") → Tennis (ou MMA si nom dans la liste)
  2. Liste équipes connues → sport direct
  3. Score extrait du match → désambiguïse les noms partagés (Monaco Foot vs Basket)

Usage :
    python3 classify_sport.py /chemin/vers/winamax-history.csv
    → écrit winamax-history.classified.csv à côté
"""

import csv
import os
import re
import sys
from pathlib import Path

# ============================================================================
# Bases de connaissances par sport
# ============================================================================

# MMA — combattants UFC/Bellator/PFL connus (vérifie en premier pour
# éviter que les noms initiale "X. Y" ne soient classés Tennis)
MMA_FIGHTERS = {
    # UFC heavyweight / light-heavyweight / middleweight / welterweight / lightweight / featherweight / bantamweight / flyweight
    "Jon Jones", "Aspinall", "Pavlovich", "Ngannou", "Gane", "Volkov", "Almeida", "Tafa",
    "Pereira", "Poatan", "Hill", "Ankalaev", "Rakic", "Prochazka", "Walker", "Reyes", "Smith", "Krylov",
    "Du Plessis", "Strickland", "Whittaker", "Costa", "Adesanya", "Cannonier", "Imavov",
    "Edwards", "Covington", "Masvidal", "Diaz", "Burns", "Usman", "Della Maddalena", "Garry",
    "Makhachev", "Volkanovski", "Holloway", "Topuria", "Tsarukyan", "Poirier", "Pimblett", "Holland",
    "Aldo", "Yair", "Cejudo", "Sandhagen", "Dvalishvili", "Yan", "Sterling", "Munhoz",
    "Pantoja", "Moreno", "Figueiredo", "Royval", "Erceg",
    "McGregor", "Khabib", "Ferguson", "Cerrone", "Rountree", "Chimaev", "Borralho",
    "Nunes", "Cyborg", "Shevchenko", "Grasso", "Pena", "Aldrich", "Andrade",
    "Allen", "Curtis", "Yusuff", "Vergara", "Gomez", "Moicano", "Roman", "Petrosyan",
    "Fiziev", "Gaethje", "Hooker", "Dariush", "Kattar", "Ortega", "Mitchell",
    "Bellator", "PFL", "Belal", "Buckley", "Kape", "Albazi", "Perez", "Schnell",
    "Brundage", "Fialho", "Brown", "Nicolau", "Saidyokub",
}

# Tennis — joueurs ATP/WTA (élargie pour couvrir le top 200 + héritage)
TENNIS_PLAYERS = {
    # ATP top 50
    "Sinner", "Alcaraz", "Djokovic", "Medvedev", "Zverev", "Tsitsipas", "Rublev", "Ruud",
    "Hurkacz", "Dimitrov", "De Minaur", "Fritz", "Paul", "Korda", "Mensik", "Khachanov",
    "Bublik", "Lehecka", "Shelton", "Musetti", "Cobolli", "Cerundolo", "Etcheverry",
    "Auger-Aliassime", "Auger Aliassime", "Fonseca", "Borges", "Galan", "Munar", "Sonego",
    "Coric", "Thompson", "Quinn", "Rune", "Ofner", "Gaubas", "Diallo", "Bergs", "Vesely",
    "Fils", "Jodar", "Davidovich", "Vallejo", "Kopriva", "Norrie", "Wawrinka",
    "Berrettini", "Goffin", "Humbert", "Tiafoe", "Eubanks", "Carballes", "Atmane",
    "Vacherot", "Rinderknech", "Moutet", "Christie", "Lehecka", "Darderi",
    "Garin", "Jarry", "Carreno-Busta", "Carreno Busta", "Davidovich Fokina",
    "Hanfmann", "Struff", "Shapovalov", "Pouille", "Halys", "Mannarino", "Müller", "Muller",
    "Bonzi", "Barrios Vera", "Ymer", "Cazaux", "Coric", "Krajinovic", "Cilic", "Wawrinka",
    "Kecmanovic", "Popyrin", "Eubanks", "Nakashima", "Tien", "Michelsen", "Sherif",
    "Nardi", "Borges", "Diallo", "Karatsev", "Kotov", "Safiullin", "Khachanov",
    "Podrez", "Bautista", "Bautista Agut",
    # WTA top 50
    "Sabalenka", "Swiatek", "Gauff", "Pegula", "Rybakina", "Jabeur", "Andreeva", "Kostyuk",
    "Bencic", "Pliskova", "Noskova", "Potapova", "Vondrousova", "Krejcikova", "Sakkari",
    "Kasatkina", "Schmiedlova", "Putintseva", "Yastremska", "Ostapenko", "Begu", "Boulter",
    "Burrage", "Cornet", "Garcia", "Mboko", "Zheng", "Watson", "Townsend", "Siegemund",
    "Zvonareva", "Siniakova", "Schiavone", "Stephens", "Anisimova", "Parks", "Jacquemot",
    "Linette", "Frech", "Putintseva", "Bouzkova", "Paolini", "Tomova", "Niemeier",
    "Maria", "Korpatsch", "Volynets", "Wang", "Yuan", "Sun", "Bouzas", "Bondar",
    "Krueger", "Davis", "Townsend", "Siegemund", "Schmiedlova",
    "Bublik", "Norrie", "Goffin", "Krueger", "Cocciaretto", "Birrell", "Pera",
    # extensions vues dans le CSV
    "Haddad Maia", "B. Haddad Maia", "Mpetshi Perricard", "G. Mpetshi Perricard",
    "Sorribes Tormo", "S. Sorribes Tormo", "De Jong", "J. De Jong",
    "L.A. Fernandez", "Fernandez", "J.J. Wolf", "Wolf", "Ruse", "E.G. Ruse",
    "K. Anderson", "Anderson", "O'Connell", "Christopher O'Connell", "Navone", "Mariano Navone",
    "Pegula", "Iga Swiatek", "Iga", "Tien", "Michelsen", "Brandon Nakashima", "Cobolli",
    "Karatsev", "Bonzi", "Halys", "Kotov", "Mannarino", "Gomez", "Coria", "Cazaux",
    "Auger Aliassime", "Felix Auger", "Etcheverry", "Tomas Martin",
    "Khachanov", "Karen Khachanov", "Stuart Bingham",
}

# Football — équipes ou compétitions
FOOTBALL_TEAMS = {
    # Top Europe
    "PSG", "Paris SG", "OM", "OL", "Lyon", "Marseille", "Lille", "AS Monaco", "Monaco FC",
    "Lens", "Rennes", "Nice", "Strasbourg", "Toulouse", "Reims", "Brest", "Nantes",
    "Auxerre", "Saint-Etienne", "Le Havre", "Angers", "Le Mans FC", "Bordeaux FC",
    "Real Madrid", "Barcelona", "FC Barcelona", "Atletico Madrid", "Atlético Madrid",
    "Sevilla", "Valencia", "Villarreal", "Real Sociedad", "Real Betis", "Athletic Bilbao",
    "Bayern Munich", "Bayern", "Dortmund", "Leipzig", "Leverkusen", "Stuttgart", "Wolfsburg",
    "Eintracht", "Hoffenheim", "Mainz", "Augsburg", "Werder", "Hertha", "Hamburg",
    "Manchester City", "Manchester United", "Liverpool", "Chelsea", "Arsenal", "Tottenham",
    "Newcastle", "Aston Villa", "West Ham", "Brighton", "Brentford", "Crystal Palace",
    "Everton", "Bournemouth", "Fulham", "Wolves", "Nottingham Forest", "Coventry",
    "Inter Milan", "Juventus", "AC Milan", "AS Roma", "Napoli", "Lazio", "Atalanta",
    "Fiorentina", "Bologna", "Torino", "Udinese", "Hellas Verona", "Sassuolo", "Genoa",
    "Lecce", "Cagliari", "Empoli", "Frosinone", "Salernitana", "Como",
    "Porto", "FC Porto", "Benfica", "Sporting", "Sporting Portugal", "Braga", "Vitoria",
    "Estrela", "CF Estrela", "Marítimo", "Maritimo", "Chaves", "Gil Vicente", "Casa Pia",
    "Ajax", "PSV", "Feyenoord", "AZ", "Twente", "Utrecht",
    "Galatasaray", "Fenerbahce", "Trabzonspor", "Besiktas", "Basaksehir", "Antalyaspor",
    "Fatih Karagumruk", "Konyaspor", "Adana", "Gaziantep",
    "Celtic", "Rangers FC", "Hibernian", "Hearts", "Aberdeen",
    "Olympiakos", "Panathinaikos", "AEK", "PAOK", "Aris", "Panserraikos", "Asteras", "AE Larisa",
    "Botafogo", "Flamengo", "Palmeiras", "Sao Paulo", "Corinthians", "Internacional",
    "Mirassol", "Atletico Mineiro", "Cruzeiro", "Gremio", "Fluminense", "Vasco",
    "Atletico Nacional", "Deportivo Pereira", "Aucas", "Independiente", "River Plate",
    "Boca Juniors", "Estudiantes", "Racing", "Velez",
    "Maccabi", "Hapoel", "Ironi", "Beitar",
    "Anderlecht", "Bruges", "Club Brugge", "Genk", "Standard", "Antwerp", "Gent",
    "RAAL La Louvière", "Zulte Waregem",
    "Mjallby", "Hammarby", "Malmo", "AIK", "Djurgardens",
    "Vikingur Reykjavik", "KR Reykjavik", "Breidablik", "Fram Reykjavik", "Stjarnan",
    "IA Akranes",
    "Bod[oø].?Glimt", "Bodo Glimt", "Lillestrom", "Rosenborg", "Molde", "Brann",
    "Copenhague", "Copenhagen", "Brondby", "Midtjylland", "Aarhus", "Silkeborg",
    "Sparta", "Spartak", "Spartak Trnava", "Slovan Bratislava", "Trnava",
    "Dinamo Zagreb", "Hajduk Split", "NK Varazdin", "NK Siroki Brijeg", "Zrinjski Mostar",
    "TSV Hartberg", "LASK", "Sturm Graz", "Rapid Vienna", "Austria Vienna", "Salzburg",
    "Widzew", "Lech Poznan", "Legia", "Pogon",
    "Debreceni", "Gyor ETO", "Ferencvaros", "MTK", "Kisvarda",
    "Wydad", "Wydad Casablanca", "WAC", "Raja", "Raja Casablanca", "FAR", "FUS Rabat",
    "RSB", "RSB Berkane", "Olympique Dcheira", "MAS", "MAS Fès", "US Yacoub Mansour",
    "Al-Nassr", "Al-Hilal", "Al-Ittihad", "Al-Qadsiah", "Al-Ahli", "Al Riyadh",
    "FC Bucheon", "Gwangju FC", "Suwon", "Ulsan", "Jeonbuk", "Pohang",
    "Kashima", "Kawasaki", "Yokohama F. Marinos", "Urawa",
    "Halmstad", "Limoges", "Bordeaux",  # peuvent matcher autre sport — désambiguïsé via score
    "Asterix Kieldrecht", "BEVO Roeselare",  # Belgique foot féminin
    "Studentski Centar", "KD Ilirija",  # ABA League — Basket à désambiguïser
    "AO Kifisias", "Annecy FC", "Nancy", "Naples", "Manchester City", "FC Barcelone",
    "Newcastle", "Kolos Kovalivka", "Rukh Lviv", "Seattle Sounders", "Iran",
    "Emirats Arabes Unis", "Pays-Bas", "Mali", "Namibie", "Gibraltar",
    "Italie", "France", "Allemagne", "Belgique", "Angleterre", "Espagne", "Portugal",
    "Suède", "Norvège", "Danemark", "Croatie", "Suisse", "Pologne", "Roumanie",
    "Hongrie", "Slovénie",  # équipes nationales (foot ou autre via score)
    "Lens", "Annecy",
    "Sada Cruzeiro", "Praia Clube",  # Volley brésil
    "Halkbank Ankara", "Ziraat Bankasi",  # Volley turc
}

# Compétitions football (matchent en plus des équipes)
FOOTBALL_LEAGUES = re.compile(
    r"\b(Ligue 1|Ligue 2|Premier League|Bundesliga|La Liga|Liga Portugal|Liga MX|Serie A|"
    r"Süper Lig|Eredivisie|Ekstraklasa|UEFA|UCL|UEL|Europa League|Conference League|"
    r"Copa Libertadores|Copa Sudamericana|MLS|Eliteserien|Allsvenskan|Veikkausliiga|"
    r"Botola|Erovnuli|Jupiler|OTP Bank|HNL|Saudi Pro|A-League|J\.?League|K\.?League|"
    r"Besta deild|J\d{1,2}\b|Liga BBVA|Liga Portugal 2|Conmebol|AFC|CAF|Coupe de France)\b",
    re.IGNORECASE,
)

# Basket — équipes NBA + EuroLeague + ABA
BASKET_TEAMS = {
    # NBA
    "Lakers", "Warriors", "Celtics", "Raptors", "Cavaliers", "Heat", "Bulls", "Knicks",
    "Nets", "76ers", "Bucks", "Pacers", "Pistons", "Hawks", "Hornets", "Magic", "Wizards",
    "Thunder", "Nuggets", "Jazz", "Spurs", "Mavericks", "Rockets", "Pelicans", "Grizzlies",
    "Timberwolves", "Trail Blazers", "Suns", "Kings", "Clippers", "Boston Celtics",
    "Toronto Raptors", "Phoenix Suns", "Detroit Pistons", "Cleveland Cavaliers",
    "Houston Rockets", "Denver Nuggets", "Oklahoma City Thunder",
    # EuroLeague / ACB / LegaBasket / Pro A
    "Real Madrid Baloncesto", "FC Barcelona Bàsquet", "Olimpia Milano", "Virtus Bologna",
    "Reyer Venezia", "Brescia", "Treviso", "Cremona", "Juvi Cremona",
    "Unicaja", "Unicaja Malaga", "Bilbao Basket", "Valencia Basket",
    "Anadolu Efes", "Fenerbahce Beko", "Maccabi Tel Aviv", "Olympiacos BC", "Panathinaikos BC",
    "Bamberg Baskets", "Bamberg",
    # ABA League
    "Studentski Centar", "KD Ilirija", "Crvena Zvezda", "Partizan",
    # Pro A France
    "Asvel", "Lyon ASVEL", "Monaco BC", "Boulogne-Levallois", "Cholet", "Limoges CSP",
    "Le Mans Sarthe Basket", "Le Mans MSB", "Strasbourg SIG",
    # NCAA / autres
    "Libertas Livorno", "Urania Milano",
}

# Hockey — NHL + AHL + KHL + Magnus + autres
HOCKEY_TEAMS = {
    "Maple Leafs", "Canadiens", "Bruins", "Penguins", "Flyers", "Capitals", "Sabres",
    "Senators", "Red Wings", "Lightning", "Panthers", "Hurricanes", "Blue Jackets",
    "Devils", "Islanders", "Stars", "Blues", "Avalanche", "Wild", "Predators", "Jets",
    "Kraken", "Oilers", "Flames", "Canucks", "Golden Knights", "Coyotes", "Sharks",
    "Ducks", "Los Angeles Kings", "San Jose Sharks", "Anaheim Ducks", "Mammoth",
    "Pittsburgh Penguins", "Vegas Golden Knights", "Utah Mammoth",
    # AHL
    "Charlotte Checkers", "Lehigh Valley Phantoms", "Laval Rocket", "Toronto Marlies",
    "Bakersfield Condors", "Coachella Valley Firebirds", "Providence Bruins",
    # Liiga / SHL / KHL
    "Ilves", "Tampere", "Ilves Tampere", "Lukko", "TPS", "JYP", "HIFK", "Tappara",
    "Frölunda", "Skellefteå", "Färjestad", "Luleå",
    # Ligue Magnus
    "Rouen", "Grenoble", "Briançon", "Cergy", "Bordeaux Boxers", "Amiens", "Angers Ducs",
    "Gap", "Chamonix", "Mulhouse",
    # DEL allemand
    "Eisbären Berlin", "Adler Mannheim", "EHC München", "Kölner Haie", "Iserlohn",
    "Fischtown",
}

# Baseball — MLB + NPB + KBO
BASEBALL_TEAMS = {
    # MLB
    "Yankees", "Red Sox", "Blue Jays", "Orioles", "Rays", "White Sox", "Guardians",
    "Tigers", "Royals", "Twins", "Astros", "Angels", "Athletics", "Mariners",
    "Texas Rangers", "Braves", "Marlins", "Mets", "Phillies", "Nationals", "Cubs",
    "Reds", "Brewers", "Pirates", "Cardinals", "Diamondbacks", "Rockies", "Dodgers",
    "Padres", "Giants",
    # NPB (japonais)
    "Hanshin Tigers", "Yokohama BayStars", "Yomiuri Giants", "Saitama Lions",
    "Saitama Seibu Lions", "Chunichi Dragons", "Hiroshima Carp", "Hiroshima Toyo Carp",
    "Tokyo Yakult Swallows", "Chiba Marines", "Chiba Lotte Marines", "Hokkaido Fighters",
    "Hokkaido Nippon-Ham Fighters", "Orix Buffaloes", "Fukuoka Hawks", "Tohoku Eagles",
    # KBO (coréen)
    "LG Twins", "Doosan Bears", "Samsung Lions", "KT Wiz", "Hanwha Eagles",
    "SSG Landers", "Lotte Giants", "Kiwoom Heroes", "NC Dinos", "KIA Tigers",
}

# Handball
HANDBALL_TEAMS = {
    "Celje", "RK Celje", "HC Ohrid", "Veszprém", "Kielce", "PSG Handball", "Barça Handball",
    "Aalborg", "Magdebourg", "THW Kiel", "Flensburg", "Flensburg-Handewitt",
    "Hanovre Burgdorf", "Limoges Handball", "Limoges H85", "Nantes HBC", "Toulouse Handball",
    "Saint-Raphaël", "Chartres Handball", "Tatabanya", "Grundfos Tatabanya",
    "Izvidjac Ljubuski", "RK Izvidjac",
}

# Rugby
RUGBY_TEAMS = {
    "Bordeaux Bègles", "UBB", "Stade Toulousain", "Toulouse Rugby", "Stade Français",
    "Racing 92", "La Rochelle", "Castres", "Lyon Rugby", "LOU", "Clermont", "ASM",
    "Montpellier", "Bayonne", "Pau", "Aviron Bayonnais",
    "Leinster", "Munster", "Saracens", "Harlequins", "Exeter Chiefs", "Bath Rugby",
    "Crusaders", "Hurricanes", "Chiefs Rugby", "All Blacks", "Springboks",
    "XV de France",
    # NRL
    "New Zealand Warriors", "Redcliffe Dolphins", "Penrith Panthers", "Brisbane Broncos",
    "Sydney Roosters", "Manly Sea Eagles",
    "Fidji", "Australie",  # rugby international (à désambiguïser via score)
}

# Volley
VOLLEY_TEAMS = {
    "Halkbank Ankara", "Ziraat Bankasi", "Vakif", "VakifBank", "Eczacibasi", "Fenerbahce Volley",
    "Bogdanka LUK Lublin", "Bogdanka", "Resovia", "Skra Belchatow", "Asseco Resovia",
    "PGE Projekt Warsaw", "PGE Lodz", "DevelopRes Rzesz", "KS Rzeszów", "Tauron Liga",
    "Conegliano", "Trentino", "Modena Volley", "Civitanova", "Lube Civitanova", "Perugia",
    "Sada Cruzeiro", "Praia Clube", "Itambé Minas", "Renata Campinas", "Cruzeiro Volley",
    "Rio Duero", "CV Melilla", "Unicaja Almeria",
}

# F1 — pilotes + écuries
F1_NAMES = {
    "Verstappen", "Hamilton", "Russell", "Leclerc", "Sainz", "Norris", "Piastri",
    "Alonso", "Stroll", "Pérez", "Perez", "Bottas", "Gasly", "Ocon", "Tsunoda",
    "Hulkenberg", "Magnussen", "Albon", "Sargeant", "Antonelli", "Bearman",
    "Mercedes", "Ferrari", "Red Bull", "McLaren", "Aston Martin", "Alpine", "Williams",
    "Haas", "Sauber", "RB",
}

# Snooker
SNOOKER_PLAYERS = {
    "Allen", "Mark Allen", "Selby", "Trump", "O'Sullivan", "Robertson", "Higgins",
    "Wilson", "Brecel", "Si Jiahui", "Zhao Xintong", "Bingham", "Stuart Bingham",
    "Wang Xinbo", "Lyu Haotian", "Vafaei", "Gilbert", "Maguire", "Lisowski",
    "Hawkins", "Carter", "Page", "Wakelin", "Murphy",
}

# Badminton
BADMINTON_PLAYERS = {
    "Akechi", "Antonsen", "Christophersen", "Buhrova", "Watanabe", "Tanaka", "Bjorkler",
    "Lin Chun-Yi", "Lin Hsiang", "Hsiang TI Lin", "Wendy Zhang", "Carrisia Jesslyn",
    "Wen Jing Xu", "Devika Sihag", "Riko Gunji", "Tomoka Miyazaki", "Neslihan Arin",
    "Tanawat Yimjit", "Mohammad Zaki Ubaidillah", "Stoeva", "Justin Hoh", "Yushi Tanaka",
    "Polina Buhrova", "Line Christophersen", "Hina Akechi",
    "Ester Nurumi", "Ozge Bayrak",
}

# eSport
ESPORT_TEAMS = {
    "T1", "Gen.G", "DRX", "Hanwha Life", "KT Rolster", "DK", "DAMWON", "DWG KIA",
    "G2 Esports", "Fnatic", "MAD Lions", "Team Liquid", "Cloud9", "100 Thieves",
    "FaZe", "NaVi", "Astralis", "FURIA", "MOUZ", "Vitality", "Spirit", "Heroic",
}

# ============================================================================
# Indices de score → sport
# ============================================================================

# Ranges typiques par sport (pour désambiguïser les noms partagés)
def score_hint(score_a, score_b):
    """Retourne le sport probable selon les deux scores."""
    if score_a is None or score_b is None:
        return None
    total = score_a + score_b
    high = max(score_a, score_b)
    diff = abs(score_a - score_b)
    # Basket : high score >= 50 quasi systématique
    if high >= 50:
        return "Basket"
    # Football : high score <= 7, total typiquement <= 8
    if total <= 8 and high <= 7:
        # Pourrait aussi être hockey, baseball
        # On retourne None et laisse les noms décider
        return None
    # Handball : 25-45 par équipe
    if 20 <= high <= 50 and 18 <= score_a <= 50 and 18 <= score_b <= 50:
        return "Handball"
    # Rugby : 10-50
    if 10 <= high <= 70 and 10 <= total <= 100:
        # Peut aussi être Hockey si rapide
        return "Rugby"
    return None


def parse_score(match_str):
    """Extrait (score_a, score_b) du champ match.
    Ex: 'Marseille1 - 1Nice' → (1, 1)
        'Trabzonspor79 - 69Galatasaray' → (79, 69)
        'Le Mans83 - 87Monaco' → (83, 87)"""
    if not match_str:
        return None, None
    # Pattern : nombre - nombre (avec ou sans espaces, scores collés)
    m = re.search(r"(\d{1,3})\s*-\s*(\d{1,3})", match_str)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


# ============================================================================
# Classification
# ============================================================================

# Pré-compile : pour chaque "atome" (mot/équipe), un sport
# On range en regex unifiées pour la perf
def build_master_regex(items, name):
    # escape + word boundaries
    escaped = sorted({re.escape(x) for x in items if x and len(x) >= 2}, key=len, reverse=True)
    return name, re.compile(r"\b(" + "|".join(escaped) + r")\b")

PATTERNS_ORDERED = [
    # Sports identifiables sans ambiguïté en premier
    build_master_regex(MMA_FIGHTERS, "MMA"),
    build_master_regex(F1_NAMES, "F1"),
    build_master_regex(SNOOKER_PLAYERS, "Snooker"),
    build_master_regex(BADMINTON_PLAYERS, "Badminton"),
    build_master_regex(BASEBALL_TEAMS, "Baseball"),
    build_master_regex(HOCKEY_TEAMS, "Hockey"),
    build_master_regex(HANDBALL_TEAMS, "Handball"),
    build_master_regex(VOLLEY_TEAMS, "Volley"),
    build_master_regex(RUGBY_TEAMS, "Rugby"),
    build_master_regex(BASKET_TEAMS, "Basket"),
    build_master_regex(TENNIS_PLAYERS, "Tennis"),
    build_master_regex(ESPORT_TEAMS, "eSport"),
    build_master_regex(FOOTBALL_TEAMS, "Football"),
]

INITIAL_NAME_RE = re.compile(r"^[A-ZÀ-ÿ][a-zà-ÿ]*\.?\s*[A-ZÀ-ÿ][A-Za-zÀ-ÿ.'-]+(\s*\/\s*[A-ZÀ-ÿ][A-Za-zÀ-ÿ.'-]+)?$")


def classify(row):
    """Retourne le sport déduit pour une ligne du CSV."""
    sport_existing = (row.get("selection_sport") or "").strip()
    # "Cotes boostées" = placement marketing, on reclasse depuis zéro
    if sport_existing and sport_existing != "?" and sport_existing != "Cotes boostées":
        return sport_existing

    sel = (row.get("selection_label") or "").strip()
    match = (row.get("selection_match") or "").strip()
    market = (row.get("selection_market") or "").strip()
    combined = f"{sel} {match} {market}"

    # Étape 1 : leagues foot (très spécifique)
    if FOOTBALL_LEAGUES.search(combined):
        # Vérifier que ce n'est pas du basket/handball déguisé
        sa, sb = parse_score(match)
        if sa is not None and max(sa, sb) >= 50:
            # gros score → basket
            return "Basket"
        if sa is not None and 18 <= max(sa, sb) <= 50 and min(sa, sb) >= 10:
            # score type handball
            return "Handball"
        return "Football"

    # Étape 2 : équipes/joueurs connus (ordre de priorité)
    candidates = []
    for sport, regex in PATTERNS_ORDERED:
        if regex.search(combined):
            candidates.append(sport)
            # premier match gagne sauf si "Football" qu'on garde en backup
            if sport != "Football":
                # désambiguïsation par score si pertinent
                sa, sb = parse_score(match)
                if sa is not None:
                    hint = score_hint(sa, sb)
                    # Si un hint contradictoire arrive (basket pour un nom Foot par ex), on suit le hint
                    if hint and hint != sport and sport == "Football":
                        return hint
                return sport
    if "Football" in candidates:
        # Vérification finale par score
        sa, sb = parse_score(match)
        if sa is not None and max(sa, sb) >= 50:
            return "Basket"
        if sa is not None and 18 <= max(sa, sb) <= 50 and min(sa, sb) >= 10:
            return "Handball"
        if sa is not None and 10 <= max(sa, sb) <= 50 and (sa + sb) >= 20:
            # Rugby possible
            if any(t in combined for t in ("Fidji", "Australie", "All Blacks", "Springboks", "Top 14", "Pro D2")):
                return "Rugby"
        return "Football"

    # Étape 3 : pattern joueur "X. Y" → Tennis (le plus fréquent)
    if INITIAL_NAME_RE.match(sel):
        # Nom dans la liste MMA explicite ?
        if any(re.search(rf"\b{re.escape(name)}\b", sel) for name in MMA_FIGHTERS):
            return "MMA"
        return "Tennis"

    # Étape 4 : selections génériques ("Match nul", "Plus de X", "Score exact"...)
    # → le sport est dans le match (équipes/joueurs)
    GENERIC_LABELS = {"Match nul", "Oui", "Non", "Double chance", "Vainqueur",
                       "1re mi-temps", "2de mi-temps", "1re manche", "2e manche",
                       "1er set", "2e set", "Plus de", "Moins de"}
    is_generic = (sel in GENERIC_LABELS) or sel.startswith(("Plus de", "Moins de")) or \
                 re.match(r"^\d+\s*-\s*\d+$", sel)  # scores style "2 - 0"

    # Pour les sélections génériques, on tente le pattern joueur sur le MATCH (pas la sel)
    if is_generic and match:
        # Cherche un nom "X. Y" dans le match
        names = re.findall(r"\b[A-ZÀ-ÿ]\.\s*[A-ZÀ-ÿ][a-zà-ÿ]+", match)
        for n in names:
            if any(re.search(rf"\b{re.escape(p)}\b", n) for p in MMA_FIGHTERS):
                return "MMA"
        if names:
            return "Tennis"  # "X. Y" présent → sport individuel
        # Pattern "Score exact 0 - 2 J1 J2 (chiffres)" → Tennis aussi
        if re.search(r"[A-ZÀ-ÿ][a-zà-ÿ]+ [A-ZÀ-ÿ][a-zà-ÿ]+\d+$", match):
            # noms complets adjacents = probablement Tennis
            return "Tennis"

    # Étape 5 : score révèle le sport
    sa, sb = parse_score(match)
    hint = score_hint(sa, sb)
    if hint:
        return hint

    # Pas trouvé
    return ""


# ============================================================================
# CLI
# ============================================================================

def main(argv):
    if len(argv) < 2:
        print("Usage: python3 classify_sport.py /chemin/winamax-history.csv")
        return 1
    path = argv[1]
    if not os.path.exists(path):
        print(f"Fichier introuvable : {path}")
        return 1

    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys()) if rows else []

    before = sum(1 for r in rows if (r.get("selection_sport") or "").strip())
    classified = 0
    for r in rows:
        original = (r.get("selection_sport") or "").strip()
        if not original or original == "?" or original == "Cotes boostées":
            sport = classify(r)
            if sport:
                r["selection_sport"] = sport
                classified += 1
            elif original == "Cotes boostées":
                # Si on ne trouve rien, vide plutôt que de garder le faux label
                r["selection_sport"] = ""

    after = sum(1 for r in rows if (r.get("selection_sport") or "").strip())

    out_path = Path(path).with_suffix(".classified.csv")
    with open(out_path, "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    settled = [r for r in rows if r.get("selection_status") in ("Gagné", "Perdu")]
    print(f"Total lignes : {len(rows)}")
    print(f"Settled : {len(settled)}")
    print(f"Sport rempli AVANT : {before} ({before/len(rows)*100:.1f}%)")
    print(f"Sport rempli APRÈS : {after} ({after/len(rows)*100:.1f}%)")
    print(f"Nouvelles classifications : +{classified}")
    print(f"\nFichier sortie : {out_path}")

    # Distribution finale
    from collections import Counter
    dist = Counter((r.get("selection_sport") or "(vide)") for r in settled)
    print(f"\nDistribution sports (settled) :")
    for s, n in dist.most_common():
        bar = "█" * int(n / len(settled) * 50)
        print(f"  {s:<22} {n:>5} ({n/len(settled)*100:>5.1f}%) {bar}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
