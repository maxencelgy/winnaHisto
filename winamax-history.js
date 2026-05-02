// Winamax — Scraper d'historique de paris (v6, détection via hash icône + scores)
//
// Découvertes DOM (inspection live 29/04) :
//   - Chaque jambe a une <img class="..." src="https://s.winamax.fr/i/icons/<HASH>.png" />
//     qui code le sport. Le hash est un identifiant Winamax stable.
//     Mapping connu : fcm3KRg4 = Baseball
//   - Pour les jambes "récentes" (avec score détaillé), l'icône est en SVG inline
//     → pas de hash extractible, on utilise alors :
//       a) Présence de cellules `.sc-fqgwrq` multiples (≥3) = Tennis (sets)
//       b) Score unique X-Y + 2 équipes = utiliser noms d'équipes/joueurs
//   - Selection joueur/équipe : <span class="sc-dcCXRD">...</span>
//   - Match : "<équipe1><score> - <score><équipe2>" dans .sc-dkkA-Dc
//
// Découvertes v2 → v3 :
//   - Chaque ticket = <div data-testid="history-item-XXXX">
//   - Réf = dans data-anchorid="history-betslip-XXXX-<REF>"
//   - Chaque jambe = <a href="/paris-sportifs/match/<id>">…</a>
//   - Statut jambe : SVG <circle fill="#70DBA6"> = Gagné, fill="#F65555"> = Perdu
//   - Le contenu des jambes est dans le DOM même replié (aria-hidden="true")
//   - "Cote totale" / "Mise" / "Gains" n'apparaissent qu'après dépliage —
//     donc on calcule la cote totale via le produit des cotes des jambes.
//
// Usage :
//   wina.diag()                       // diag : nb tickets + 1ère extraction
//   await wina.run({ maxPages: 1 })   // test sur 1 page
//   await wina.run()                  // tout

(() => {
  const SCROLL_DELAY = 200;
  const PAGE_SETTLE_MS = 900;
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // ---- Cards ----
  function findTicketCards() {
    return [...document.querySelectorAll('[data-testid^="history-item-"]')];
  }

  // ---- Champs ticket ----
  function extractRef(card) {
    const anchor = card.querySelector('[data-anchorid^="history-betslip-"]');
    if (anchor) {
      const m = anchor.getAttribute('data-anchorid').match(/history-betslip-(?:[A-Z0-9]+-)?([A-Z0-9]+)$/);
      if (m) return m[1];
    }
    const m = (card.textContent || '').match(/Réf\s*:\s*([A-Z0-9]+)/);
    return m ? m[1] : '';
  }

  function extractStatus(card) {
    // Le 1er div feuille tout en haut contient "Gagné"/"Perdu"/"En cours"
    const leaves = [...card.querySelectorAll('div')].filter((d) => d.children.length === 0);
    for (const d of leaves.slice(0, 8)) {
      const t = norm(d.textContent);
      if (/^(Gagné|Perdu|En cours|Annulé|Remboursé)$/.test(t)) return t;
    }
    const m = (card.textContent || '').match(/\b(Gagné|Perdu|En cours|Annulé|Remboursé)\b/);
    return m ? m[1] : '';
  }

  function extractType(card) {
    const leaves = [...card.querySelectorAll('div')].filter((d) => d.children.length === 0);
    for (const d of leaves.slice(0, 12)) {
      const t = norm(d.textContent);
      if (/^(Simple|Combiné|Système)$/.test(t)) return t;
    }
    return '';
  }

  function extractDate(card) {
    const m = (card.textContent || '').match(/(\d{1,2}h\d{2})\s*-\s*(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})/i);
    if (!m) return '';
    const months = { janvier:'01','février':'02', mars:'03', avril:'04', mai:'05', juin:'06', juillet:'07','août':'08', septembre:'09', octobre:'10', novembre:'11','décembre':'12' };
    return `${m[4]}-${months[m[3].toLowerCase()]}-${String(m[2]).padStart(2,'0')} ${m[1].replace('h',':')}`;
  }

  function extractStakeGain(card) {
    const t = card.textContent || '';
    let stake = '', stakeType = '', gain = '';
    let m = t.match(/Mise\s*Freebets[^\d-]*(\d+[.,]\d+)/i);
    if (m) { stake = m[1].replace(',', '.'); stakeType = 'Freebet'; }
    else if ((m = t.match(/\bMise\b[^\d-]*(\d+[.,]\d+)/i))) { stake = m[1].replace(',', '.'); stakeType = 'Cash'; }
    m = t.match(/Gains?[^\d-]*(\d+[.,]\d+)/i);
    if (m) gain = m[1].replace(',', '.');
    return { stake, stakeType, gain };
  }

  function extractTotalOdds(card) {
    const t = card.textContent || '';
    const idx = t.indexOf('Cote totale');
    if (idx >= 0) {
      const m = t.slice(idx, idx + 80).match(/(\d+[.,]\d+)/);
      if (m) return m[1].replace(',', '.');
    }
    return '';
  }

  // ---- Détection statut jambe via couleur SVG ----
  function legStatusFromSvg(scope) {
    // On cherche le PREMIER svg-circle pertinent (généralement dans l'en-tête de la jambe)
    const svgs = [...scope.querySelectorAll('svg circle[fill]')];
    for (const c of svgs) {
      const fill = (c.getAttribute('fill') || '').toUpperCase();
      if (fill === '#70DBA6') return 'Gagné';
      if (fill === '#F65555') return 'Perdu';
    }
    // Fallback : aria-label
    const html = scope.outerHTML || '';
    const a = html.match(/aria-label="(Gagné|Perdu|Annulé|Remboursé)"/i);
    if (a) return a[1];
    return '';
  }

  // ---- Jambes : chaque <a href="/paris-sportifs/match/..."> = 1 jambe ----
  function extractLegs(card, ticketStatus, ticketType) {
    const matchLinks = [...card.querySelectorAll('a[href*="/paris-sportifs/match/"]')];
    const legs = [];

    for (const a of matchLinks) {
      // Spans : market puis selection
      const spans = [...a.querySelectorAll('span')].map((s) => norm(s.textContent)).filter(Boolean);

      // Cote : feuille dont le texte est "X.YZ" ou "X,YZ"
      const oddsLeaf = [...a.querySelectorAll('div')]
        .filter((d) => d.children.length === 0)
        .map((d) => norm(d.textContent))
        .find((t) => /^\d+[.,]\d{1,2}$/.test(t));
      const odds = oddsLeaf ? oddsLeaf.replace(',', '.') : '';

      // Market / Selection : les 2 premiers <span> non-numériques
      let market = '', selection = '';
      const nonNum = spans.filter((s) => !/^\d+([.,]\d+)?$/.test(s) && s.length < 80);
      if (nonNum.length >= 1) market = nonNum[0];
      if (nonNum.length >= 2) selection = nonNum[1];

      // Match : ligne avec score "X - Y" (les <span>X</span> - <span>Y</span> + noms)
      const matchText = norm(a.textContent).replace(/^.*?(\d+\s*-\s*\d+)/, (s) => s);
      const matchLine = (norm(a.textContent).match(/[A-ZÀ-Ÿ][^]{0,120}\d+\s*-\s*\d+\s*[A-ZÀ-Ÿ][^]{0,120}/) || [''])[0];

      const sport = detectSportSmart(a, card);

      // Statut de cette jambe : l'icône check/cross sur cette ligne
      // (l'en-tête du ticket contient un compteur global avec couleurs aussi → on ne regarde QUE l'<a>)
      const status = legStatusFromSvg(a) || (matchLinks.length === 1 ? ticketStatus : '');

      legs.push({
        market,
        selection,
        match: norm(matchLine).slice(0, 200),
        odds,
        status,
        sport,
        match_id: (a.getAttribute('href') || '').match(/match\/(\d+)/)?.[1] || '',
      });
    }

    if (legs.length === 0) {
      // fallback Simple
      const odds = extractTotalOdds(card);
      legs.push({ market: '', selection: '', match: '', odds, status: ticketStatus, sport: detectSportSmart(card, card), match_id: '' });
    }
    return legs;
  }

  // ===== Détection sport (multi-niveaux) =====
  const HARDCODED_SPORTS = {
    '1': 'Football', '2': 'Tennis', '3': 'Rugby', '4': 'Basket',
    '5': 'Hockey', '6': 'Handball', '7': 'Volley', '9': 'Cyclisme',
    '11': 'Boxe', '12': 'MMA', '13': 'Golf', '16': 'F1',
    '17': 'Baseball', '20': 'Badminton', '23': 'Football américain',
    '31': 'eSport', '44': 'Snooker', '117': 'eSport', '190': 'Tennis de table',
    '208': 'Ski', '9992': 'Divers',
  };

  // Catégories Winamax qui NE SONT PAS des sports (placements marketing)
  const NOT_A_SPORT = /^(Cotes? boostées?|Boost|Promo|Mission|Tournois|Spéciaux|Politique|Divertissement|Cinéma|Téléréalité|Top mises)$/i;

  // Mapping dynamique ID→nom via la nav latérale (filtre les non-sports)
  const SPORT_MAP = (() => {
    const m = { ...HARDCODED_SPORTS };
    for (const a of document.querySelectorAll('a[href*="/paris-sportifs/sports/"]')) {
      const href = a.getAttribute('href') || '';
      // Skip les URLs marketing
      if (/(cote[s]?[- ]boost|promo|mission|special|tournoi)/i.test(href)) continue;
      const match = href.match(/\/sports\/(\d+)(?:[\/?#-]|$)/);
      if (!match) continue;
      const id = match[1];
      const t = norm(a.textContent);
      if (!t || t.length <= 1 || t.length >= 30) continue;
      if (NOT_A_SPORT.test(t)) continue;
      if (!/^[A-Za-zÀ-ÿ0-9 .'-]+$/.test(t)) continue;
      m[id] = t;
    }
    return m;
  })();

  // Patterns texte ordonnés du PLUS spécifique au moins (ex: UFC/NHL avant Football générique)
  const TEXT_PATTERNS = [
    // Acronymes uniques (pas d'ambiguïté)
    ['MMA', /\b(UFC|Bellator|PFL|ONE Championship|MMA Fighting)\b/i],
    ['MMA', /\b(McGregor|Khabib|Adesanya|Volkanovski|Pereira|Jon Jones|Du Plessis|Strickland|Whittaker|Poatan|Topuria|Makhachev|Holloway|Aldo|Costa|O'Malley|Garbrandt|Cejudo|Dvalishvili|Yan|Sterling|Cyborg|Nunes|Shevchenko|Pantoja|Moreno|Figueiredo|Chimaev|Sandhagen|Kattar|Ortega|Volkov|Ngannou|Gane|Pavlovich|Aspinall|Hill|Ankalaev|Rakic|Prochazka|Walker|Reyes|Smith|Krylov|Chiesa|Burns|Usman|Edwards|Covington|Masvidal|Diaz|Cerrone|Ferguson|Pimblett|Holland|Curtis|Allen|Andrade|Yusuff|Aldrich|Vergara|Gomez|Tafa|Moicano|Tsarukyan|Almeida|Roman|Petrosyan)\b/],
    ['Hockey', /\b(NHL|KHL|SHL|Liiga|DEL|Ligue Magnus|AHL|Hockey sur glace)\b/i],
    ['Hockey', /\b(Maple Leafs|Canadiens|Bruins|Penguins|Flyers|Capitals|Sabres|Senators|Red Wings|Lightning|Panthers|Hurricanes|Blue Jackets|Devils|Islanders|Stars|Blues|Avalanche|Wild|Predators|Jets|Kraken|Oilers|Flames|Canucks|Golden Knights|Coyotes|Sharks|Ducks|Los Angeles Kings|San Jose Sharks|Anaheim Ducks)\b/],
    ['Baseball', /\b(MLB|NPB|KBO|World Series)\b/i],
    ['Baseball', /\b(Yankees|Red Sox|Blue Jays|Orioles|Rays|White Sox|Guardians|Tigers|Royals|Twins|Astros|Angels|Athletics|Mariners|Texas Rangers|Braves|Marlins|Mets|Phillies|Nationals|Cubs|Reds|Brewers|Pirates|Cardinals|Diamondbacks|Rockies|Dodgers|Padres|Giants)\b/],
    ['Football américain', /\b(NFL|Super Bowl|College Football|NCAA Football)\b/i],
    ['Basket', /\b(NBA|EuroLeague|EuroLigue|Pro A Basket|Betclic Élite|BNXT|ACB|G[- ]?League|Liga Endesa|VTB|EuroCup|LegaBasket|Lega Basket|FIBA|Ligue ABA|Champions League Basketball)\b/i],
    ['Basket', /\b(Lakers|Warriors|Celtics|Raptors|Cavaliers|Miami Heat|Chicago Bulls|Knicks|Brooklyn Nets|76ers|Bucks|Pacers|Pistons|Hawks|Hornets|Orlando Magic|Wizards|Thunder|Nuggets|Utah Jazz|Spurs|Mavericks|Rockets|Pelicans|Grizzlies|Timberwolves|Trail Blazers|Phoenix Suns|Sacramento Kings|Clippers|Unicaja|Olimpia Milano|Virtus Bologna|Reyer Venezia)\b/],
    ['F1', /\b(F1|Formula 1|Formule 1|Grand Prix|GP de|Pole Position|MotoGP|Moto[2-3]|Verstappen|Hamilton|Russell|Leclerc|Sainz|Norris|Piastri|Alonso|Stroll|Pérez|Bottas|Gasly|Ocon|Tsunoda|Hulkenberg|Magnussen|Albon|Sargeant)\b/i],
    ['Tennis', /\b(ATP|WTA|Roland[- ]Garros|Wimbledon|US Open|Australian Open|Open d'Australie|Indian Wells|Miami Open|Monte[- ]Carlo|Cincinnati|Shanghai|Paris[- ]Bercy|Challenger|ITF|Davis Cup|Billie Jean|Tournoi de.*tennis)\b/],
    ['Tennis', /\b(Sinner|Alcaraz|Djokovic|Medvedev|Zverev|Tsitsipas|Rublev|Ruud|Hurkacz|Dimitrov|Sabalenka|Swiatek|Gauff|Pegula|Rybakina|Jabeur|Andreeva|Kostyuk|Cobolli|Cerundolo|Etcheverry|Mensik|Auger[- ]Aliassime|Khachanov|Bublik|Lehecka|Shelton|De Minaur|Musetti|Fritz|Paul|Korda|Bencic|Pliskova|Noskova|Potapova|Vondrousova|Krejcikova|Sakkari|Kasatkina|Schmiedlova|Putintseva|Yastremska|Ostapenko|Begu|Boulter|Burrage|Cornet|Garcia|Mboko|Zheng|Rinderknech|Moutet|Atmane|Vacherot|Dart|Christie|Osaka|Watson|Townsend|Siegemund|Zvonareva|Siniakova|Schiavone|Stephens|Anisimova|Fils|Jodar|Bublik|Auger|Davidovich|Vallejo|Kopriva|Norrie|Wawrinka|Berrettini|Goffin|Humbert|Tiafoe|Eubanks|Borges|Galan|Munar|Carballes|Sonego|Coric|Thompson|Quinn|Rune|Ofner|Gaubas|Diallo|Fonseca|Bergs|Vesely)\b/],
    ['Tennis', /\b\w\.\s?\w+\s+(?:vs|-)\s+\w\.\s?\w+\b/], // pattern "F. Cobolli vs L. Musetti"
    ['Snooker', /\b(Snooker|Crucible|Mosconi|UK Championship.*Snooker|World Championship.*Snooker)\b/i],
    ['Badminton', /\b(Thomas Cup|Uber Cup|Sudirman|Badminton|BWF|Akechi|Antonsen|Christophersen|Buhrova)\b/i],
    ['Tennis de table', /\b(WTT|Table Tennis|Ping[- ]?pong|Tennis de table|ITTF)\b/i],
    ['eSport', /\b(LCS|LEC|LCK|LPL|CS:?GO|CS2|Dota|Valorant|League of Legends|LoL|Rocket League|Counter[- ]Strike|MSI|Worlds.*League)\b/i],
    ['Cyclisme', /\b(Tour de France|Giro|Vuelta|Paris[- ]Roubaix|Liège.*Liège|Monument|UCI World|Critérium|Tirreno|Pogačar|Vingegaard|Roglič|Van Aert|Van Der Poel|Evenepoel|Pidcock)\b/i],
    ['Golf', /\b(PGA|LPGA|Masters Augusta|US Open Golf|The Open Championship|Ryder Cup|DP World Tour|FedEx Cup)\b/i],
    ['Boxe', /\b(WBA|WBC|IBF|WBO|Boxing.*Champion|Boxe anglaise|Boxe poids|Fury|Usyk|Joshua|Wilder|Crawford|Spence|Canelo|Bivol|Beterbiev|Inoue|Lomachenko)\b/i],
    ['Rugby', /\b(Top 14|Pro D2|Six Nations|Champions Cup Rugby|Challenge Cup Rugby|Super Rugby|NRL|Premiership Rugby|XV de France|All Blacks|Springboks)\b/i],
    ['Handball', /\b(Liqui Moly|Lidl Starligue|HBL|Liga ASOBAL|EHF|Handball|LNH|Flensburg|Tatabanya|Kielce|Veszprém|Magdebourg|Aalborg|THW Kiel|Barça Handball|PSG Handball)\b/i],
    ['Volley', /\b(VNL|Volleyball|SuperLega|CEV|Halkbank|Ziraat|Tauron|TAURON|PlusLiga|DevelopRes|Rzesz|Resovia|Bogdanka|Conegliano|Trentino|Modena|Civitanova|Perugia|Lube|Vakif|Eczacibasi|Sada Cruzeiro|Praia Clube)\b/i],
    ['Ski', /\b(Slalom|Géant|Descente|Super[- ]G|Combiné nordique|Coupe du monde.*ski|Biathlon)\b/i],
    // Football en dernier (génériques qui peuvent matcher du noise dans d'autres sports)
    ['Football', /\b(Ligue 1|Ligue 2|Premier League|Bundesliga|La Liga|Liga Portugal|Liga MX|Serie A|Süper Lig|Eredivisie|Ekstraklasa|UEFA|UCL|UEL|Europa League|Conference League|Copa Libertadores|Copa Sudamericana|MLS|Eliteserien|Allsvenskan|Veikkausliiga|Botola|Erovnuli|Jupiler|OTP Bank|HNL|First League|Saudi Pro|A-League|J.?League|K.?League|Besta deild)\b/i],
    ['Football', /\b(Real Madrid|Barcelona|Atlético|Atletico Madrid|PSG|OM|OL|Lille|AS Monaco|Bayern Munich|Dortmund|Leipzig|Leverkusen|Manchester United|Manchester City|Liverpool|Chelsea|Arsenal|Tottenham|Inter Milan|Juventus|AC Milan|AS Roma|Napoli|Lazio|Atalanta|Porto|Benfica|Sporting|Ajax|PSV|Feyenoord|Galatasaray|Fenerbahce|Trabzonspor|Besiktas|Celtic|Rangers FC|Olympiakos|Panathinaikos|Botafogo|Internacional|Bod[oø].?Glimt|Maccabi|Hapoel|Ironi|Anderlecht|Bruges|Genk|Standard|Mjallby|Vikingur Reykjavik|KR Reykjavik|Al-Nassr|Al-Qadsiah|Al-Hilal|Al-Ittihad|Wydad|Raja|Mirassol|Aucas|Sada|Chaves|Gil Vicente|Sporting Portugal|Benfica B|FC Estrela|Trnava|Zlín|Atalanta|Vitoria|Coventry|Dijon|Marítimo|Lorient|Strasbourg|Stuttgart|Werder Brême|Mayence|Hoffenheim|Augsburg|Wolfsburg|Hertha)\b/],
    ['Football', /\bJ\d{1,2}\b.*\b(Liga|Ligue|Liga Portugal|Allsvenskan|Süper|Botola|Eliteserien)\b/i],
  ];

  // Mots à exclure (placement marketing Winamax)
  const SKIP_PATTERNS = [/Cotes? boostées?/i, /Mission Quotidienne/i, /Boost/i];

  const SLUG_MAP = {
    football: 'Football', soccer: 'Football', tennis: 'Tennis',
    basketball: 'Basket', basket: 'Basket', hockey: 'Hockey',
    baseball: 'Baseball', mma: 'MMA', boxing: 'Boxe', boxe: 'Boxe',
    rugby: 'Rugby', handball: 'Handball', volleyball: 'Volley',
    volley: 'Volley', badminton: 'Badminton', golf: 'Golf',
    formula: 'F1', f1: 'F1', cycling: 'Cyclisme', cyclisme: 'Cyclisme',
    esport: 'eSport', esports: 'eSport', snooker: 'Snooker',
    'table-tennis': 'Tennis de table', tabletennis: 'Tennis de table',
    ski: 'Ski', americanfootball: 'Football américain', nfl: 'Football américain',
  };

  // Normalise un texte issu de textContent : insère des espaces autour des mots collés
  function normalizeForMatch(txt) {
    return txt
      .replace(/([a-zà-ÿ])([A-ZÀ-ÿ])/g, '$1 $2')
      .replace(/([A-Za-zÀ-ÿ])(\d)/g, '$1 $2')
      .replace(/(\d[.,]\d+)([A-Za-zÀ-ÿ])/g, '$1 $2')
      .replace(/\s+/g, ' ');
  }

  // ===== Mapping hash d'icône Winamax → sport =====
  // À enrichir au fur et à mesure : window.__hashStats (collecté en runtime) permet
  // de voir les hash inconnus pour les classifier manuellement.
  const ICON_HASH_TO_SPORT = {
    'fcm3KRg4': 'Baseball', // Hanshin/Yokohama/Yomiuri/Saitama (NPB)
    // les autres seront détectés via TEXT_PATTERNS et collectés dans __hashStats
  };

  // Pattern sélection "X. Y" ou "X.Y" (joueur individuel : Tennis/MMA/Boxe/Snooker/Badminton)
  const INITIAL_NAME_RE = /^[A-ZÀ-ÿ][a-zà-ÿ]*\.?\s*[A-ZÀ-ÿ][A-Za-zÀ-ÿ.'-]+$/;

  // Détection sport — utilise les SELECTORS PROPRES (pas le textContent bruité)
  function detectSportSmart(scope, fallbackScope) {
    if (!scope?.querySelector) return '';

    // Texte propre : selection + match (sans bruit de cote/score/UI)
    const sel = scope.querySelector('.sc-dcCXRD')?.textContent?.trim() || '';
    const matchTxt = scope.querySelector('.sc-dkkA-Dc')?.textContent?.trim() ||
                     scope.querySelector('.sc-cUOzhM')?.textContent?.trim() || '';

    // Fallback noms équipes (jambes "détaillées" Tennis avec sets)
    const teamNames = [...scope.querySelectorAll('.sc-mkoLC, .sc-fhOrUh')]
                        .map(e => e.textContent?.trim()).filter(Boolean).join(' ');

    // Texte combiné, normalisé
    let cleanTxt = `${sel} ${matchTxt} ${teamNames}`.replace(/\s+/g, ' ').trim();
    cleanTxt = normalizeForMatch(cleanTxt);
    for (const skip of SKIP_PATTERNS) cleanTxt = cleanTxt.replace(skip, ' ');

    // Score multi-set (Tennis) — selector spécifique
    const setCells = scope.querySelectorAll('.sc-fqgwrq, [class*="fqgwrq"]');
    const hasMultiSets = setCells.length >= 4;

    // 1) Patterns sport spécifiques sur le texte propre
    for (const [name, re] of TEXT_PATTERNS) {
      if (re.test(cleanTxt)) return name;
    }

    // 2) Pattern selection "Initiale. Nom" → sport individuel
    if (INITIAL_NAME_RE.test(sel.trim())) {
      // Multi-sets confirme Tennis ; sinon Tennis par défaut (le user a 1176 Tennis vs 441 MMA)
      return 'Tennis';
    }

    // 3) Fallback texte de la card complète (rare)
    if (fallbackScope && fallbackScope !== scope) {
      let fbTxt = normalizeForMatch(fallbackScope.textContent || '');
      for (const skip of SKIP_PATTERNS) fbTxt = fbTxt.replace(skip, ' ');
      for (const [name, re] of TEXT_PATTERNS) {
        if (re.test(fbTxt)) return name;
      }
    }
    return '';
  }

  // Conservé pour compat (utilisé nulle part désormais mais évite ReferenceError)
  function detectSportFromText(t) {
    for (const [name, re] of TEXT_PATTERNS) {
      if (re.test(t)) return name;
    }
    return '';
  }

  function extractRow(card) {
    const ref = extractRef(card);
    const ticketStatus = extractStatus(card);
    const ticketType = extractType(card);
    const date = extractDate(card);
    const { stake, stakeType, gain } = extractStakeGain(card);
    let totalOdds = extractTotalOdds(card);
    const legs = extractLegs(card, ticketStatus, ticketType);

    // Calcul cote totale si non visible (ticket replié)
    if (!totalOdds && legs.length > 0 && legs.every((l) => l.odds)) {
      const product = legs.reduce((acc, l) => acc * parseFloat(l.odds), 1);
      totalOdds = product.toFixed(2);
    }

    return legs.map((leg) => ({
      ticket_ref: ref,
      ticket_date: date,
      ticket_type: ticketType,
      ticket_status: ticketStatus,
      ticket_total_odds: totalOdds,
      ticket_stake: stake,
      ticket_stake_type: stakeType,
      ticket_gain: gain,
      ticket_legs_count: legs.length,
      selection_market: leg.market,
      selection_label: leg.selection,
      selection_match: leg.match,
      selection_match_id: leg.match_id,
      selection_sport: leg.sport,
      selection_odds: leg.odds,
      selection_status: leg.status,
    }));
  }

  // ---- Pagination (multi-stratégies) ----
  function findPaginationButtons() {
    return [...document.querySelectorAll('button, a, [role="button"]')].filter((b) => {
      const t = norm(b.textContent);
      return /^\d+$/.test(t) || /^(suivant|next|>|»|précédent|previous|<|«)$/i.test(t);
    });
  }

  let currentPage = 1;
  function findNextButton() {
    // 1) Bouton avec aria-label / title explicite
    const ariaCandidates = [...document.querySelectorAll('button, a, [role="button"]')];
    for (const b of ariaCandidates) {
      const aria = (b.getAttribute('aria-label') || b.getAttribute('title') || '').toLowerCase();
      if (/page suivante|next page|suivant|next/i.test(aria) && !b.disabled && b.getAttribute('aria-disabled') !== 'true') {
        return b;
      }
    }
    // 2) Bouton texte "Suivant" / "Next" / ">" / "»"
    const btns = findPaginationButtons();
    let next = btns.find((b) => /^(suivant|next|>|»)$/i.test(norm(b.textContent)) && !b.disabled);
    if (next) return next;
    // 3) Bouton numérique = currentPage + 1
    next = btns.find((b) => norm(b.textContent) === String(currentPage + 1));
    if (next) return next;
    // 4) Boutons avec SVG flèche droite (chevron-right) + non disabled
    const svgBtns = [...document.querySelectorAll('button:has(svg), a:has(svg), [role="button"]:has(svg)')];
    for (const b of svgBtns) {
      const svg = b.querySelector('svg');
      const html = (svg?.outerHTML || '').toLowerCase();
      // chevron droite : path "M..." pointant à droite, ou class chevron-right/arrow-right
      if (/(chevron[- ]?right|arrow[- ]?right|page[- ]?next|caret[- ]?right)/i.test(html + (b.className || ''))) {
        if (!b.disabled && b.getAttribute('aria-disabled') !== 'true') return b;
      }
    }
    return null;
  }

  function diagPagination() {
    const btns = findPaginationButtons();
    const txts = btns.map((b) => norm(b.textContent)).filter(Boolean);
    const next = findNextButton();
    console.log(`[wina-pag] currentPage=${currentPage}, paginationButtons=${JSON.stringify(txts)}, hasNext=${!!next}, nextText='${next ? norm(next.textContent) : ''}', nextAria='${next?.getAttribute?.('aria-label') || ''}'`);
  }

  async function autoScroll() {
    let last = -1;
    for (let i = 0; i < 30; i++) {
      window.scrollBy(0, 700);
      await sleep(SCROLL_DELAY);
      const h = document.documentElement.scrollHeight;
      if (h === last) break;
      last = h;
    }
    window.scrollTo(0, 0);
    await sleep(150);
  }

  async function goNextPage() {
    const btn = findNextButton();
    if (!btn || btn.disabled || btn.getAttribute('aria-disabled') === 'true') return false;
    btn.scrollIntoView({ behavior: 'instant', block: 'center' });
    btn.click();
    currentPage++;
    await sleep(PAGE_SETTLE_MS);
    return true;
  }

  // ---- Diagnostic ----
  function diag() {
    const cards = findTicketCards();
    const next = findNextButton();
    const pag = findPaginationButtons().map((b) => norm(b.textContent)).filter(Boolean);
    console.log(`[wina-diag] cards=${cards.length}, hasNext=${!!next}, paginationButtons=${JSON.stringify(pag)}`);
    if (cards[0]) {
      console.log('[wina-diag] 1ère card → rows :', extractRow(cards[0]));
    }
    if (cards[1]) {
      console.log('[wina-diag] 2ème card → rows :', extractRow(cards[1]));
    }
    return { cards: cards.length, hasNext: !!next, paginationButtons: pag };
  }

  // ---- Diag SVG sport (le SVG inline en début de jambe encode le sport) ----
  function diagSportSvg() {
    const sportSigSamples = {};
    for (const card of findTicketCards()) {
      for (const a of card.querySelectorAll('a[href*="/paris-sportifs/match/"]')) {
        // Le 1er <svg> dans .sc-iGYsGe ou similaire = icône sport
        const svgWrap = a.querySelector('[class*="iGYsGe"], [class*="bnidXr"]');
        const svg = (svgWrap || a).querySelector('svg');
        if (!svg) continue;

        // Signature stable du SVG : viewBox + 1ère partie du path "d="
        const viewBox = svg.getAttribute('viewBox') || '';
        const path = svg.querySelector('path');
        const d = path?.getAttribute('d') || '';
        const sig = `vb=${viewBox}|d0=${d.slice(0, 40)}`;

        if (!sportSigSamples[sig]) sportSigSamples[sig] = { count: 0, examples: [] };
        sportSigSamples[sig].count++;
        if (sportSigSamples[sig].examples.length < 5) {
          const sel = a.querySelector('.sc-dcCXRD')?.textContent?.trim() || '';
          const matchTxt = a.querySelector('.sc-dkkA-Dc')?.textContent?.trim() ||
                           a.querySelector('.sc-cUOzhM')?.textContent?.trim() ||
                           (a.textContent || '').replace(/\s+/g,' ').slice(0, 60).trim();
          sportSigSamples[sig].examples.push({ sel, match: matchTxt.slice(0, 50) });
        }
      }
    }
    console.log('[wina-svg] signatures SVG sport — chacune devrait être un sport');
    console.table(Object.entries(sportSigSamples).map(([sig, v]) => ({
      sig: sig.slice(0, 60),
      count: v.count,
      ex1: v.examples[0]?.sel || '',
      match1: v.examples[0]?.match || '',
      ex2: v.examples[1]?.sel || '',
      match2: v.examples[1]?.match || '',
    })));
    window.__svgSigs = sportSigSamples;
    return sportSigSamples;
  }

  // ---- Diag des hash d'icônes équipe (utile pour mapping équipe → sport) ----
  function diagIcons() {
    const hashSamples = {};
    for (const card of findTicketCards()) {
      for (const a of card.querySelectorAll('a[href*="/paris-sportifs/match/"]')) {
        const img = a.querySelector('img[src*="/icons/"]');
        if (!img) continue;
        const src = img.getAttribute('src') || '';
        const hashMatch = src.match(/\/icons\/([^./]+)\./);
        if (!hashMatch) continue;
        const hash = hashMatch[1];
        if (!hashSamples[hash]) hashSamples[hash] = { count: 0, examples: [] };
        hashSamples[hash].count++;
        if (hashSamples[hash].examples.length < 4) {
          const sel = a.querySelector('.sc-dcCXRD')?.textContent?.trim() || '';
          const matchTxt = a.querySelector('.sc-dkkA-Dc')?.textContent?.trim() ||
                           a.querySelector('.sc-cUOzhM')?.textContent?.trim() || '';
          hashSamples[hash].examples.push({ sel, match: matchTxt.slice(0, 60) });
        }
      }
    }
    console.log('[wina-icons] hash → samples (équipes individuelles, pas sports)');
    console.table(Object.entries(hashSamples).map(([h, v]) => ({
      hash: h, count: v.count,
      example1: v.examples[0]?.sel || '',
      match1: v.examples[0]?.match || '',
    })));
    return hashSamples;
  }

  // ---- Boucle principale ----
  async function run({ maxPages = 200 } = {}) {
    const allRows = [];
    const seenRefs = new Set();
    currentPage = 1;

    for (let page = 1; page <= maxPages; page++) {
      await autoScroll();
      const cards = findTicketCards();
      let added = 0, skipped = 0;
      for (const card of cards) {
        const ref = extractRef(card);
        if (!ref) { skipped++; continue; }
        if (seenRefs.has(ref)) continue;
        seenRefs.add(ref);
        const rows = extractRow(card);
        allRows.push(...rows);
        added += rows.length;
      }
      console.log(`[wina] page ${page} — cards=${cards.length}, +${added} lignes (skipped sans ref=${skipped}, total ${allRows.length})`);

      if (cards.length === 0) break;
      const moved = await goNextPage();
      if (!moved) {
        console.log('[wina] arrêt : pas de bouton suivant détecté.');
        diagPagination();
        break;
      }
    }

    api.rows = allRows;
    if (!allRows.length) { console.warn('[wina] aucune ligne. Lance wina.diag().'); return allRows; }
    download(toCSV(allRows), `winamax-history-${new Date().toISOString().slice(0,10)}.csv`);
    stats(allRows);
    return allRows;
  }

  function toCSV(rows) {
    if (!rows.length) return '';
    const headers = Object.keys(rows[0]);
    const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    return '\uFEFF' + [headers.join(','), ...rows.map((r) => headers.map((h) => esc(r[h])).join(','))].join('\n');
  }
  function download(content, filename) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: filename });
    document.body.appendChild(a); a.click(); a.remove();
  }
  function stats(rows) {
    const settled = rows.filter((r) => r.selection_status === 'Gagné' || r.selection_status === 'Perdu');
    const buckets = {};
    for (const r of settled) {
      const o = parseFloat(r.selection_odds);
      if (!o) continue;
      const k = (Math.round(o * 10) / 10).toFixed(1);
      buckets[k] ??= { won: 0, total: 0 };
      buckets[k].total++;
      if (r.selection_status === 'Gagné') buckets[k].won++;
    }
    const table = Object.entries(buckets)
      .sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]))
      .map(([odds, v]) => ({ cote: odds, n: v.total, gagnés: v.won, winrate: ((v.won/v.total)*100).toFixed(1)+'%', EV: (((v.won/v.total)*parseFloat(odds))-1).toFixed(3) }));
    console.log(`[wina] Stats par tranche de cote (n=${settled.length})`);
    console.table(table);
  }

  const api = { run, diag, diagPagination, diagIcons, diagSportSvg, toCSV, stats, rows: [] };
  window.wina = api;
  console.log('[wina v7] prêt. Détection via selectors propres (.sc-dcCXRD + .sc-dkkA-Dc).');
  console.log('  wina.diagIcons()                  // liste les hash d\'icônes pour mapping');
  console.log('  await wina.run({maxPages: 1})     // test 1 page');
  console.log('  await wina.run()                  // tout');
})();
