// =============================================================================
// winamax-calendar.js v4 — scrape calendar Winamax + cotes (tous sports)
//
// v4 : capture PROGRESSIVE pendant scroll (fix virtual scrolling)
//      + patterns sports élargis (championnats nationaux + équipes NBA/MLB/NFL/NHL)
//      + cleanup propre des sélections (préfixes volume Winamax)
//
// Usage :
//   1. https://www.winamax.fr/paris-sportifs/calendar
//   2. F12 → Console → "autoriser le collage" si demandé
//   3. Coller, puis :
//        await wina.scan()        // scroll auto + capture progressive
//        wina.edges()
//        wina.csv()
// =============================================================================
(() => {
  const log = (...a) => console.log("%c[wina-cal]", "color:#60a5fa;font-weight:bold", ...a);
  const warn = (...a) => console.warn("%c[wina-cal]", "color:#fbbf24;font-weight:bold", ...a);

  const EDGE = {
    minOdds: 1.15,
    maxOdds: 1.65,
    goodSports: ["Tennis", "MMA", "Football", "Basket", "Hockey", "F1", "Boxe"],
    badSports: ["Baseball"],
  };

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fnum = (s) => {
    if (s == null) return null;
    const n = parseFloat(String(s).replace(",", "."));
    return Number.isFinite(n) ? n : null;
  };

  // ---- 1) Mapping ID → sport (hardcodé Winamax + fallback dynamique) ----
  const HARDCODED_SPORTS = {
    "1": "Football", "2": "Tennis", "3": "Rugby", "4": "Basket",
    "5": "Hockey", "6": "Handball", "7": "Volley", "9": "Cyclisme",
    "11": "Boxe", "12": "MMA", "13": "Golf", "16": "F1",
    "17": "Baseball", "20": "Badminton", "23": "Football américain",
    "31": "eSport", "44": "Snooker", "117": "eSport", "190": "Tennis de table",
    "208": "Ski", "9992": "Divers",
  };
  const SPORT_MAP = (() => {
    const m = { ...HARDCODED_SPORTS };
    for (const a of document.querySelectorAll('a[href*="/paris-sportifs/sports/"]')) {
      const href = a.getAttribute("href") || "";
      const match = href.match(/\/sports\/(\d+)(?:[\/?#-]|$)/);
      if (!match) continue;
      const id = match[1];
      const t = (a.textContent || "").trim();
      if (t && t.length > 1 && t.length < 30 && /^[A-Za-zÀ-ÿ0-9 .'-]+$/.test(t)) {
        m[id] = t;
      }
    }
    return m;
  })();

  // ---- 2) Patterns texte ÉLARGIS ----
  const TEXT_PATTERNS = [
    // Football : ligues majeures + championnats nationaux mondiaux
    ["Football", /\b(Ligue 1|Ligue 2|Premier League|Bundesliga|La Liga|Liga Portugal|Liga MX|Serie A|Süper Lig|Eredivisie|Ekstraklasa|Pro League|Championship|UEFA|UCL|UEL|Europa|Conference|Copa|Libertadores|Sudamericana|MLS|J\d{1,2}|Eliteserien|Allsvenskan|Veikkausliiga|Botola|Erovnuli|Jupiler|OTP Bank|Super League|Spartak|Slovan|Sparta|HNL|First League|Premiership|Saudi Pro|A-League|J.?League|K.?League)\b/i],
    // Football équipes connues (filet de sécurité)
    ["Football", /\b(Real Madrid|Barcelona|Atlético|PSG|Lyon|Marseille|Lille|Monaco|Bayern|Dortmund|Leipzig|Leverkusen|Manchester|Liverpool|Chelsea|Arsenal|Tottenham|City|United|Inter|Juventus|Milan|Roma|Napoli|Lazio|Atalanta|Porto|Benfica|Sporting|Ajax|PSV|Feyenoord|Galatasaray|Fenerbahce|Trabzonspor|Besiktas|Celtic|Rangers|Olympiakos|Panathinaikos|Dinamo|Lillestrom|Bod[oø].?Glimt|Maccabi|Hapoel|Ironi|Asterix|RAAL|Zulte|Anderlecht|Bruges|Genk|Standard|FC Porto|FC Barcelona)\b/],
    // Tennis
    ["Tennis", /\b(ATP|WTA|Madrid|Roland[- ]Garros|Wimbledon|US Open|Australian Open|Set|Simples|Doubles|Challenger|ITF|Davis Cup|Billie Jean|Open d'Australie|Indian Wells|Miami Open|Monte[- ]Carlo|Cincinnati|Shanghai|Paris[- ]Bercy)\b/i],
    // Basket : ligues majeures + équipes NBA
    ["Basket", /\b(NBA|EuroLeague|EuroLigue|Pro A|Betclic Élite|BNXT|ACB|G[- ]?League|Liga Endesa|VTB|EuroCup|LegaBasket|Lega Basket|Serie A2|LBA|Champions League Basketball|FIBA)\b/i],
    ["Basket", /\b(Lakers|Warriors|Celtics|Raptors|Cavaliers|Heat|Bulls|Knicks|Nets|76ers|Bucks|Pacers|Pistons|Hawks|Hornets|Magic|Wizards|Thunder|Nuggets|Jazz|Spurs|Mavericks|Rockets|Pelicans|Grizzlies|Timberwolves|Trail Blazers|Suns|Kings|Clippers)\b/],
    ["Basket", /\b(Treviso|Brescia|Olimpia Milano|Virtus Bologna|Reyer Venezia|Real Madrid Baloncesto|FC Barcelona Bàsquet)\b/],
    // Hockey
    ["Hockey", /\b(NHL|KHL|SHL|Liiga|DEL|Ligue Magnus|AHL|Hockey)\b/i],
    ["Hockey", /\b(Maple Leafs|Canadiens|Bruins|Rangers|Penguins|Flyers|Capitals|Sabres|Senators|Red Wings|Lightning|Panthers|Hurricanes|Blue Jackets|Devils|Islanders|Stars|Blues|Avalanche|Wild|Predators|Jets|Kraken|Oilers|Flames|Canucks|Golden Knights|Coyotes|Sharks|Ducks|Kings)\b/],
    // Baseball
    ["Baseball", /\b(MLB|NPB|KBO|World Series)\b/i],
    ["Baseball", /\b(Yankees|Red Sox|Blue Jays|Orioles|Rays|White Sox|Guardians|Tigers|Royals|Twins|Astros|Angels|Athletics|Mariners|Rangers|Braves|Marlins|Mets|Phillies|Nationals|Cubs|Reds|Brewers|Pirates|Cardinals|Diamondbacks|Rockies|Dodgers|Padres|Giants)\b/],
    // MMA / Combat
    ["MMA", /\b(UFC|Bellator|PFL|ONE Championship|MMA)\b/i],
    ["Boxe", /\b(Boxe|Boxing|WBA|WBC|IBF|WBO)\b/i],
    // F1 + sports moteur
    ["F1", /\b(F1|Formula 1|Formule 1|Grand Prix|GP de|Pole Position|MotoGP|Moto[2-3])\b/i],
    // Rugby
    ["Rugby", /\b(Top 14|Pro D2|Six Nations|Champions Cup|Challenge Cup|Super Rugby|NRL|Premiership Rugby|United Rugby Championship)\b/i],
    // Handball
    ["Handball", /\b(Liqui Moly|Lidl Starligue|HBL|Liga ASOBAL|EHF|Handball|Bundesliga.*hand|Champions League.*hand)\b/i],
    // Volley
    ["Volley", /\b(VNL|Volleyball|Volley|Ligue A.*volley|SuperLega|CEV)\b/i],
    // Badminton
    ["Badminton", /\b(Thomas Cup|Uber Cup|Sudirman|Badminton|BWF)\b/i],
    // eSport
    ["eSport", /\b(LCS|LEC|LCK|LPL|CS:?GO|CS2|Dota|Valorant|League of Legends|Rocket League|Counter[- ]Strike|Esports|eSports|MSI|Worlds.*League)\b/i],
    // Snooker / Billard
    ["Snooker", /\b(Snooker|World Championship.*Snooker|UK Championship|Crucible|Mosconi)\b/i],
    ["Billard", /\b(Billard|Pool|Eurotour|Predator World)\b/i],
    // Tennis de table
    ["Tennis de table", /\b(WTT|Table Tennis|Ping[- ]?pong|Tennis de table|ITTF)\b/i],
    // Cyclisme
    ["Cyclisme", /\b(Tour de France|Giro|Vuelta|Paris[- ]Roubaix|Liège|Monument|UCI World|Critérium|Tirreno)\b/i],
    // Golf
    ["Golf", /\b(PGA|LPGA|Masters|US Open Golf|The Open|Ryder Cup|DP World Tour|FedEx Cup)\b/i],
    // Ski
    ["Ski", /\b(Ski|Slalom|Géant|Descente|Super[- ]G|Combiné|Coupe du monde.*ski|Biathlon)\b/i],
    // NFL
    ["Football américain", /\b(NFL|Super Bowl|College Football|NCAA Football)\b/i],
  ];

  function detectSport(card) {
    // 1) lien /sports/X
    const links = [...card.querySelectorAll('a[href*="/paris-sportifs/sports/"]')];
    for (const a of links) {
      const m = (a.getAttribute("href") || "").match(/\/sports\/(\d+)/);
      if (m && SPORT_MAP[m[1]]) return SPORT_MAP[m[1]];
    }
    // 2) ancêtres
    let n = card.parentElement;
    for (let i = 0; i < 8 && n; i++, n = n.parentElement) {
      const a = n.querySelector('a[href*="/paris-sportifs/sports/"]');
      if (a) {
        const mm = (a.getAttribute("href") || "").match(/\/sports\/(\d+)/);
        if (mm && SPORT_MAP[mm[1]]) return SPORT_MAP[mm[1]];
      }
    }
    // 3) icône
    for (const ic of card.querySelectorAll("img[alt], svg[aria-label], [aria-label], [data-sport], [title]")) {
      const v = ic.getAttribute("alt") || ic.getAttribute("aria-label") || ic.dataset?.sport || ic.getAttribute("title") || "";
      const trimmed = v.trim();
      if (trimmed && trimmed.length < 30 && /^[A-Za-zÀ-ÿ0-9 .'-]+$/.test(trimmed)) {
        for (const v of Object.values(SPORT_MAP)) {
          if (trimmed.toLowerCase() === v.toLowerCase()) return v;
        }
      }
    }
    // 4) heuristique texte
    const txt = card.textContent || "";
    for (const [name, re] of TEXT_PATTERNS) {
      if (re.test(txt)) return name;
    }
    return "?";
  }

  // ---- 3) Cotes ----
  function extractOdds(card) {
    const btns = [...card.querySelectorAll('[data-testid^="odd-button"]')];
    const out = [];
    const seen = new Set();
    for (const b of btns) {
      const txt = (b.textContent || "").replace(/\s+/g, " ").trim();
      const oddMatch = txt.match(/(\d+[,.]\d{2})\s*$/);
      if (!oddMatch) continue;
      const odds = fnum(oddMatch[1]);
      if (!odds || odds < 1.01 || odds > 1000) continue;
      let label = txt.replace(oddMatch[1], "").replace(/[€,]/g, "").trim();
      // CLEANUP : Winamax préfixe parfois le label avec un volume "1234NomEquipe"
      // → on enlève les chiffres de tête
      label = label.replace(/^\d{1,5}(?=[A-ZÀ-ÿ])/, "").trim();
      const tid = b.getAttribute("data-testid") || "";
      if (seen.has(tid)) continue;
      seen.add(tid);
      out.push({ label: label || "?", odds, testid: tid });
    }
    return out;
  }

  // ---- 4) Métadonnées match ----
  function extractMatchMeta(card) {
    const candidates = [];
    for (const el of card.querySelectorAll("span, div, p, h3, h4")) {
      if (el.children.length > 0) continue;
      const t = (el.textContent || "").trim();
      if (!t) continue;
      if (t.length >= 2 && t.length <= 50 && /[A-ZÀ-ÿ]/.test(t) && !/\d+[,.]\d{2}/.test(t) && !/^\d+%/.test(t)) {
        if (/^(Vainqueur|Match nul|Plus|Moins|Score|Total|Premier|Buts?|Mi[- ]temps)/i.test(t)) continue;
        candidates.push({ el, t });
      }
    }
    const fullTxt = (card.textContent || "").replace(/\s+/g, " ");
    const time = (fullTxt.match(/\b([01]?\d|2[0-3])[h:][0-5]\d\b/) || [])[0] || "";
    const day =
      (fullTxt.match(/\b(Aujourd['']?hui|Demain|Hier)\b/i) || [])[0] ||
      (fullTxt.match(/\b(Lun|Mar|Mer|Jeu|Ven|Sam|Dim)\.?\s*\d{1,2}\s*[a-zéû]+\.?/i) || [])[0] ||
      (fullTxt.match(/\b\d{1,2}\/\d{1,2}(\/\d{2,4})?\b/) || [])[0] ||
      "";

    let name = "";
    if (candidates.length >= 2) {
      // exclure les compétitions du choix des équipes
      const COMP_KEYWORDS = /\b(Liga|Cup|League|Championship|Pro|Serie|Coupe|Trophée|Tour|Premiership|Elite|Magnus|HBL|VNL|NBA|NHL|MLB|NFL|UFC|ATP|WTA|Bundesliga|J\d|Botola|Eliteserien|Erovnuli|Eredivisie|Ekstraklasa|Süper|OTP|Jupiler|Spartak|Liiga|HNL|Saudi|MLS|MotoGP|Snooker|Crucible|Tournoi|Final|Tour de|Vuelta|Giro)\b/i;
      const filtered = candidates.filter(
        (c) => !COMP_KEYWORDS.test(c.t) && c.t.length >= 3 && /^[A-ZÀ-ÿ]/.test(c.t)
      );
      const teams = [];
      // garder l'ordre DOM, filtrer doublons
      for (const c of filtered) {
        if (teams.length >= 2) break;
        if (!teams.find((x) => x.t === c.t || c.t.includes(x.t) || x.t.includes(c.t))) teams.push(c);
      }
      if (teams.length >= 2) {
        teams.sort((a, b) => {
          const ar = a.el.compareDocumentPosition(b.el);
          return ar & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
        });
        name = `${teams[0].t} - ${teams[1].t}`;
      } else if (teams.length === 1) {
        name = teams[0].t;
      }
    }
    if (!name) {
      const dashMatch = fullTxt.match(/([A-ZÀ-ÿ][A-Za-zÀ-ÿ0-9. ]{2,40})\s+(?:vs|-)\s+([A-ZÀ-ÿ][A-Za-zÀ-ÿ0-9. ]{2,40})/);
      if (dashMatch) name = `${dashMatch[1].trim()} - ${dashMatch[2].trim()}`;
      else name = fullTxt.slice(0, 80);
    }

    // compétition
    let comp = "";
    for (const c of candidates) {
      if (/\b(Liga|Cup|League|Championship|Pro|Serie|Bundesliga|J\d|Botola|Eliteserien|Erovnuli|Eredivisie|Ekstraklasa|Süper|OTP|Jupiler|HNL|MLS|NBA|NHL|MLB|NFL|UFC|ATP|WTA|MotoGP|Snooker)\b/i.test(c.t)) {
        comp = c.t; break;
      }
    }
    if (!comp) {
      let p = card.parentElement;
      for (let i = 0; i < 6 && p; i++, p = p.parentElement) {
        const h = p.querySelector("h2, h3, [data-testid*='header'], [data-testid*='title']");
        if (h && h.textContent && h.textContent.trim().length < 60) {
          comp = h.textContent.trim();
          break;
        }
      }
    }

    const link = card.querySelector("a[href]");
    const url = link ? new URL(link.getAttribute("href"), location.origin).href : "";

    return { name, when: [day, time].filter(Boolean).join(" "), competition: comp, url };
  }

  // ---- 5) Capture progressive (anti virtual-scroll) ----
  // Au lieu de scroll-puis-scan, on capture à chaque palier.
  // Dédup par data-testid de la card.
  const captured = new Map(); // testid → row(s)

  function captureCurrent() {
    const cards = [...document.querySelectorAll('[data-testid^="match-card"]')];
    let added = 0;
    for (const card of cards) {
      const tid = card.getAttribute("data-testid");
      if (!tid || captured.has(tid)) continue;
      const sport = detectSport(card);
      const meta = extractMatchMeta(card);
      const odds = extractOdds(card);
      if (!odds.length) continue;
      const rows = odds.map((o) => ({
        sport,
        when: meta.when,
        competition: meta.competition,
        match: meta.name,
        selection: o.label,
        odds: o.odds,
        url: meta.url,
        card_testid: tid,
        odd_testid: o.testid,
      }));
      captured.set(tid, rows);
      added++;
    }
    return added;
  }

  async function scrollAndCapture(maxIter = 80, step = 700, settle = 700) {
    captureCurrent(); // initial
    let stable = 0;
    let lastSize = captured.size;
    let pos = 0;
    const maxScroll = () => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);

    for (let i = 0; i < maxIter; i++) {
      pos = Math.min(pos + step, maxScroll());
      window.scrollTo({ top: pos, behavior: "instant" });
      await sleep(settle);
      const added = captureCurrent();
      if (i % 5 === 0) log(`  palier ${i}: pos=${pos}, total cards capturées=${captured.size}`);
      // arrêt si fin de page atteinte ET pas de nouvelles cards depuis plusieurs paliers
      if (pos >= maxScroll() - 50) {
        if (captured.size === lastSize) {
          stable++;
          if (stable >= 3) break;
        } else stable = 0;
        lastSize = captured.size;
      }
    }
    window.scrollTo(0, 0);
    await sleep(300);
    captureCurrent(); // capture finale après retour en haut
  }

  // ---- 6) Scan ----
  async function scan({ maxIter = 80, step = 700 } = {}) {
    captured.clear();
    log("scroll + capture progressive…");
    await scrollAndCapture(maxIter, step);

    const out = [];
    for (const rows of captured.values()) out.push(...rows);
    state.rows = out;

    const matches = new Set(out.map((r) => r.card_testid));
    const sportsCount = {};
    for (const r of out) sportsCount[r.sport] = (sportsCount[r.sport] || 0) + 1;
    log(`✅ ${out.length} cotes / ${matches.size} matchs uniques`);
    log("sports :", sportsCount);
    return out;
  }

  // ---- 7) Edges ----
  function edges() {
    const list = state.rows.filter(
      (r) => r.odds >= EDGE.minOdds && r.odds <= EDGE.maxOdds && !EDGE.badSports.includes(r.sport),
    );
    const byMatch = {};
    for (const r of list) {
      const k = r.card_testid || r.match;
      if (!byMatch[k] || r.odds < byMatch[k].odds) byMatch[k] = r;
    }
    const picks = Object.values(byMatch).sort((a, b) => a.odds - b.odds);
    console.table(picks.map((p) => ({
      sport: p.sport,
      match: (p.match || "").slice(0, 50),
      cote: p.odds,
      sel: (p.selection || "").slice(0, 25),
      when: p.when,
      good: EDGE.goodSports.includes(p.sport) ? "✓" : "",
    })));
    log(`${picks.length} edges (cote ${EDGE.minOdds}-${EDGE.maxOdds}, hors ${EDGE.badSports.join("/")})`);
    return picks;
  }

  // ---- 8) CSV ----
  function toCSV(rows) {
    const cols = ["sport", "competition", "when", "match", "selection", "odds", "url"];
    const esc = (v) => {
      const s = String(v ?? "");
      return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    return [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  }
  function downloadCSV(filename = `winamax-calendar-${new Date().toISOString().slice(0, 10)}.csv`) {
    if (!state.rows.length) return warn("Aucune ligne. Lance d'abord await wina.scan()");
    const csv = toCSV(state.rows);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
    log(`CSV téléchargé : ${filename} (${state.rows.length} lignes)`);
  }

  // ---- 9) Diag ----
  function diag() {
    const cards = document.querySelectorAll('[data-testid^="match-card"]');
    log({
      url: location.href,
      sportMapSize: Object.keys(SPORT_MAP).length,
      sportMapPreview: Object.entries(SPORT_MAP).slice(0, 12),
      cardsVisibles: cards.length,
      capturedSoFar: captured.size,
      docHeight: document.body.scrollHeight,
      sampleCard: cards[0] ? {
        sport: detectSport(cards[0]),
        meta: extractMatchMeta(cards[0]),
        odds: extractOdds(cards[0]),
      } : null,
    });
  }

  const state = { rows: [] };
  window.wina = { scan, edges, csv: downloadCSV, diag, EDGE, SPORT_MAP, get rows() { return state.rows; } };
  log(`v4 prêt. ${Object.keys(SPORT_MAP).length} sports mappés. Capture progressive activée.`);
  log("  await wina.scan()    // scroll + capture (5-15s)");
  log("  wina.edges()");
  log("  wina.csv()");
})();
