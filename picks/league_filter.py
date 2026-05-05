# Filtre centralisé des ligues autorisées (Winamax FR)
# Utilisé à la fois par le scraper live et le backtest engine pour garantir une cohérence parfaite.

WINAMAX_LEAGUES = {
    "football": [
        "premier league", "laliga", "la liga", "serie a", "bundesliga", "ligue 1",
        "championship", "laliga 2", "la liga 2", "serie b", "bundesliga 2", "ligue 2",
        "champions league", "europa league", "conference", "conference league", "uefa",
        "eredivisie", "liga portugal", "primeira liga", "pro league", "süper lig",
        "trendyol süper", "mls", "liga mx", "brasileirão", "brasileirao",
        "primera división", "primera a", "primera b", "argentina", "ecuador serie a",
        "coupe de france", "fa cup", "copa del rey", "coppa italia", "dfb-pokal", "coupe",
        "world cup", "euro 2", "copa america", "africa cup", "uefa nations league", "nations league",
        "k league", "k-league", "k league 1", "j1 league", "j league", "j2 league",
        "saudi pro", "pro league", "qatar stars",
        "super league", "extraliga", "fortuna liga", "niké liga", "veikkausliiga",
        "a lyga", "parva liga", "erovnuli", "ligat ha", "ligat haal", "premiership",
        "championship round", "championship play-off", "fifa intercontinental"
    ],
    "basketball": [
        "nba", "wnba", "euroleague", "eurocup", "betclic élite", "pro a",
        "acb", "liga endesa", "lega basket", "serie a", "bbl", "champions league",
        "champions league asia"
    ],
    "ice-hockey": [
        "nhl", "khl", "shl", "liiga", "ligue magnus", "del", "national league",
        "extraliga", "elite league", "swiss"
    ],
    "baseball": ["mlb", "npb"],
    "tennis": [
        "atp", "wta", "grand slam", "masters", "australian open", "roland garros",
        "wimbledon", "us open", "miami", "indian wells", "monte carlo", "madrid",
        "rome", "cincinnati", "shanghai", "paris masters"
    ],
}

REJECT_LEAGUES = [
    "doubles", "qualifying", "u23", "u21", "u19", "u18", "u17", "reserve", "youth",
    "next pro", "regionalliga", "série c", "serie c", "i-league", "exhibition",
    "women, qualif", "men, qualif", "challenger round", "k league 2",
    "league 1, championship", "knockout stage qualifying", "primera b nacional",
    "ptt ", "utr ",
    # Barrages / playoffs de relégation — rarement sur Winamax FR
    "relegation/promotion", "relegation round", "relegation playoff",
    "playout", "rel/prom",
    # Ligues exotiques pas sur Winamax FR
    "indonesian", "chinese super league", "canadian championship",
]

# Liste stricte de pays à rejeter pour éviter les faux-positifs sur des noms de ligues génériques ("Premier League", "Primera División")
REJECT_CATEGORIES = [
    "israel", "costa rica", "egypt", "cyprus", "uganda", "kenya", "russia", 
    "ukraine", "ghana", "malta", "sudan", "nigeria", "tanzania", "rwanda", 
    "zambia", "bulgaria", "faroe islands", "maldives", "mauritania", 
    "sri lanka", "burundi", "cambodia", "ethiopia", "bahrain", "azerbaijan",
    "kazakhstan", "kuwait"
]

def is_league_ok(sport, league, category="", excluded_user_leagues=None):
    """
    Retourne True si la ligue est autorisée selon les critères Winamax stricts.
    """
    if not league:
        return False
    
    lg = league.lower()
    cat = category.lower() if category else ""
    
    # 1. Vérifier les exclusions utilisateur dynamiques
    if excluded_user_leagues:
        if any(e in lg for e in excluded_user_leagues):
            return False
            
    # 2. Vérifier les catégories/pays rejetés en dur
    if cat and any(r in cat for r in REJECT_CATEGORIES):
        return False
        
    # 3. Vérifier les mots-clés de ligues interdites (U21, women, etc.)
    if any(r in lg for r in REJECT_LEAGUES):
        return False
        
    # 4. Vérifier si ça match la whitelist officielle
    return any(p in lg for p in WINAMAX_LEAGUES.get(sport, []))
