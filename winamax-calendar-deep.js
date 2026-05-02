/**
 * winamax-calendar-deep.js — v1
 * Scraper "deep" qui capture TOUS les marchés (vainqueur + handicap + totals + sets + etc.)
 * pour chaque match du calendar.
 *
 * Usage :
 *   1. Ouvrir https://www.winamax.fr/paris-sportifs/calendar
 *   2. Console (F12) → coller ce script
 *   3. await wina.run()             // capture calendar standard (1N2)
 *   4. await wina.deep({ max: 30 }) // capture les marchés secondaires sur top N matchs
 *   5. wina.csvDeep()                // télécharge le CSV "deep"
 *
 * Le CSV deep contient une ligne par cote disponible :
 *   match, competition, market, selection, odds, url
 *
 * Stratégie : pour chaque match capturé, fetch l'URL de la page match via window.fetch
 * (même origine, donc cookies disponibles), parse le HTML, extrait les boutons de cotes
 * avec leurs labels et le titre du marché parent.
 *
 * Note : ce script suppose que wina.run() a déjà tourné et peuplé window.wina.rows
 * avec des matchs ayant le champ `url` non vide.
 */

(() => {
  const TAG = "[wina-deep]";
  const log = (...a) => console.log(TAG, ...a);
  const warn = (...a) => console.warn(TAG, ...a);

  // ---- Extraction des marchés depuis un HTML de page match ----
  function extractFromHTML(html) {
    const doc = new DOMParser().parseFromString(html, "text/html");

    // Stratégie 1 : Winamax SPA Next.js — chercher __NEXT_DATA__
    const nextData = doc.querySelector('script#__NEXT_DATA__');
    if (nextData) {
      try {
        const json = JSON.parse(nextData.textContent);
        const markets = walkForMarkets(json);
        if (markets.length) return markets;
      } catch (e) {
        warn("__NEXT_DATA__ parse failed:", e.message);
      }
    }

    // Stratégie 2 : __INITIAL_STATE__ ou __PRELOADED_STATE__ inline
    const scripts = doc.querySelectorAll("script:not([src])");
    for (const s of scripts) {
      const txt = s.textContent || "";
      const patterns = [
        /window\.__INITIAL_STATE__\s*=\s*({[\s\S]*?});\s*(?:window|<\/script>|$)/,
        /window\.__PRELOADED_STATE__\s*=\s*({[\s\S]*?});\s*(?:window|<\/script>|$)/,
        /window\.__APOLLO_STATE__\s*=\s*({[\s\S]*?});\s*(?:window|<\/script>|$)/,
      ];
      for (const p of patterns) {
        const m = txt.match(p);
        if (m) {
          try {
            const json = JSON.parse(m[1]);
            const markets = walkForMarkets(json);
            if (markets.length) return markets;
          } catch {}
        }
      }
    }

    // Stratégie 3 : DOM brut — boutons de cotes avec data-testid
    return extractFromDOM(doc);
  }

  // Walk récursif d'une structure JSON pour repérer les objets "marché"/"cote"
  function walkForMarkets(root) {
    const found = [];
    const seen = new WeakSet();

    function walk(obj, ctx = {}) {
      if (!obj || typeof obj !== "object" || seen.has(obj)) return;
      seen.add(obj);

      // Heuristique : objet "outcome/selection" si a un prix + label
      const price = obj.price ?? obj.odds ?? obj.cote ?? obj.value;
      const label = obj.label ?? obj.name ?? obj.selectionLabel ?? obj.title;
      if (typeof price === "number" && price >= 1.01 && price < 1000 && typeof label === "string") {
        found.push({
          market: ctx.marketName || obj.marketName || obj.market || "?",
          selection: label.trim(),
          odds: price,
        });
      }

      // Detect "market" containers and propagate their name to children
      const newCtx = { ...ctx };
      if (obj.marketName || obj.market || obj.type) {
        newCtx.marketName = obj.marketName || obj.market || obj.type;
      }

      if (Array.isArray(obj)) {
        for (const v of obj) walk(v, newCtx);
      } else {
        for (const k in obj) {
          if (Object.prototype.hasOwnProperty.call(obj, k)) walk(obj[k], newCtx);
        }
      }
    }
    walk(root);
    return found;
  }

  // Extraction depuis le DOM rendu (fallback)
  function extractFromDOM(doc) {
    const found = [];
    const sections = doc.querySelectorAll('[data-testid^="market"], [class*="Market"], section');
    sections.forEach((sec) => {
      const headEl = sec.querySelector('h2, h3, h4, [class*="MarketTitle"], [data-testid*="market-title"]');
      const marketName = headEl ? headEl.textContent.trim().slice(0, 60) : "?";
      const buttons = sec.querySelectorAll('[data-testid^="odd-button"], button[class*="odd"], button[class*="Odd"]');
      buttons.forEach((b) => {
        const txt = (b.textContent || "").replace(/\s+/g, " ").trim();
        const m = txt.match(/(\d+[.,]\d+)/);
        if (!m) return;
        const odds = parseFloat(m[1].replace(",", "."));
        const sel = txt.replace(m[0], "").trim();
        if (sel && odds >= 1.01) {
          found.push({ market: marketName, selection: sel, odds });
        }
      });
    });
    return found;
  }

  // ---- Fetch d'une page match avec retry ----
  async function fetchMatch(url, retries = 2) {
    for (let i = 0; i <= retries; i++) {
      try {
        const r = await fetch(url, { credentials: "same-origin" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return await r.text();
      } catch (e) {
        if (i === retries) {
          warn(`fetch ${url} failed:`, e.message);
          return null;
        }
        await new Promise((r) => setTimeout(r, 800));
      }
    }
  }

  // ---- Scan du DOM pour récupérer les URLs des match cards ----
  function scanMatchUrlsFromDOM() {
    const urls = new Map();
    // Stratégie 1 : ancres <a href="/paris-sportifs/match/...">
    document.querySelectorAll('a[href*="/paris-sportifs/"]').forEach((a) => {
      const href = a.getAttribute("href") || "";
      // Filtre les liens qui ressemblent à des matchs (contiennent /match/ ou /sport/.../match-...)
      if (!/\/match[\/\-]|\/paris-sportifs\/sport\/.+\/.+/.test(href)) return;
      // Texte du lien (souvent contient le nom du match)
      const text = (a.innerText || a.textContent || "").replace(/\s+/g, " ").trim();
      if (text.length < 3) return;
      // Construit l'URL absolue
      const fullUrl = href.startsWith("http") ? href : new URL(href, window.location.origin).href;
      // Évite les doublons : utilise l'URL comme clé
      if (!urls.has(fullUrl)) {
        urls.set(fullUrl, { url: fullUrl, label: text.slice(0, 80) });
      }
    });

    // Stratégie 2 : data-testid pour match-card avec onclick handler
    document.querySelectorAll('[data-testid^="match-card"], [data-testid*="match"]').forEach((el) => {
      const link = el.querySelector("a[href]") || el.closest("a[href]");
      if (link) {
        const href = link.getAttribute("href");
        if (href && !/^javascript:/.test(href)) {
          const fullUrl = href.startsWith("http") ? href : new URL(href, window.location.origin).href;
          if (!urls.has(fullUrl)) {
            const text = (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 80);
            urls.set(fullUrl, { url: fullUrl, label: text });
          }
        }
      }
    });

    return Array.from(urls.values());
  }

  // ---- Main : itère sur les matchs du calendar ----
  async function runDeep(opts = {}) {
    const max = opts.max ?? 20;
    const delay = opts.delay ?? 600;
    const skipExisting = opts.skipExisting ?? true;

    // Strat 1 : utilise window.wina.rows si disponible avec URLs
    let list = [];
    if (window.wina && window.wina.rows) {
      const matchUrls = new Map();
      for (const r of window.wina.rows) {
        if (r.match && r.url && !matchUrls.has(r.match)) {
          matchUrls.set(r.match, { url: r.url, competition: r.competition || "" });
        }
      }
      list = Array.from(matchUrls.entries()).map(([match, v]) => ({
        match,
        url: v.url,
        competition: v.competition,
      }));
    }

    // Strat 2 (fallback) : scanne le DOM courant pour trouver les URLs
    if (list.length === 0) {
      log("Pas de URLs dans wina.rows → scan du DOM courant...");
      const domUrls = scanMatchUrlsFromDOM();
      log(`URLs trouvées dans le DOM : ${domUrls.length}`);
      if (domUrls.length === 0) {
        warn("Aucune URL match détectée. Scrolle dans le calendar puis relance.");
        return;
      }
      list = domUrls.map((u) => ({ match: u.label, url: u.url, competition: "" }));
    }

    list = list.slice(0, max);
    log(`Deep scrape sur ${list.length} matchs (delay ${delay}ms entre chaque)`);

    const all = window.wina.deepRows || [];
    const seenMatches = new Set(all.map((r) => r.match));

    let i = 0;
    for (const item of list) {
      i++;
      const match = item.match;
      const url = item.url;
      const competition = item.competition || "";
      if (skipExisting && seenMatches.has(match)) {
        log(`(${i}/${list.length}) skip ${match} (déjà fait)`);
        continue;
      }

      const html = await fetchMatch(url);
      if (!html) {
        log(`(${i}/${list.length}) ❌ ${match}`);
        continue;
      }
      const markets = extractFromHTML(html);
      log(`(${i}/${list.length}) ✓ ${match.slice(0, 40)} → ${markets.length} cotes`);

      for (const m of markets) {
        all.push({ match, competition, ...m, url });
      }
      seenMatches.add(match);
      await new Promise((r) => setTimeout(r, delay));
    }

    window.wina.deepRows = all;
    log(`Total cotes deep capturées : ${all.length}`);
    log(`Téléchargez avec : wina.csvDeep()`);
    return all;
  }

  // ---- Export CSV ----
  function csvEscape(v) {
    const s = String(v ?? "");
    if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  function downloadCSVDeep() {
    const rows = window.wina?.deepRows || [];
    if (!rows.length) {
      warn("Rien à exporter. Lance wina.deep() d'abord.");
      return;
    }
    const headers = ["match", "competition", "market", "selection", "odds", "url"];
    const csv = [headers.join(",")]
      .concat(rows.map((r) => headers.map((h) => csvEscape(r[h])).join(",")))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    const date = new Date().toISOString().slice(0, 10);
    a.download = `winamax-calendar-deep-${date}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    log(`CSV téléchargé (${rows.length} lignes)`);
  }

  // ---- Diagnostic : tester sur 1 match pour vérifier les sélecteurs ----
  async function diagDeep(matchName) {
    const r = (window.wina?.rows || []).find((x) => (x.match || "").includes(matchName));
    if (!r || !r.url) {
      warn(`Pas de match correspondant à "${matchName}". Disponibles :`);
      const sample = [...new Set((window.wina?.rows || []).map((x) => x.match))].slice(0, 10);
      sample.forEach((s) => console.log("  -", s));
      return;
    }
    log(`Diag fetch ${r.url}`);
    const html = await fetchMatch(r.url);
    if (!html) return;
    log(`HTML reçu : ${html.length} chars`);
    const markets = extractFromHTML(html);
    log(`Marchés extraits : ${markets.length}`);
    console.table(markets.slice(0, 30));
    return markets;
  }

  // ---- Diagnostic des URLs disponibles ----
  function scanUrls() {
    const urls = scanMatchUrlsFromDOM();
    log(`URLs trouvées dans le DOM courant : ${urls.length}`);
    console.table(urls.slice(0, 20));
    return urls;
  }

  // ---- Diagnostic des match cards : dump structure pour reverse-engineering ----
  function diagCard() {
    log("=== Inspecting match cards structure ===");

    // Cherche tous les éléments candidats
    const candidates = [
      ...document.querySelectorAll('[data-testid^="match-card"]'),
      ...document.querySelectorAll('[data-testid*="match"]'),
      ...document.querySelectorAll('[class*="MatchCard"]'),
      ...document.querySelectorAll('[class*="match-card"]'),
    ];
    const seen = new Set();
    const unique = candidates.filter((el) => !seen.has(el) && seen.add(el));
    log(`Candidates trouvés : ${unique.length}`);

    if (unique.length === 0) {
      log("Aucune match card. Test alternatif : éléments avec onclick + texte court ressemblant à un match...");
      const allClickable = document.querySelectorAll('[onclick], [role="button"], button');
      log(`Éléments cliquables : ${allClickable.length}`);
      return;
    }

    // Inspecte la 1ère card
    const card = unique[0];
    const info = {
      tag: card.tagName,
      "data-testid": card.getAttribute("data-testid"),
      classes: card.className.toString().slice(0, 100),
      "data-*": Object.fromEntries(
        [...card.attributes].filter((a) => a.name.startsWith("data-")).map((a) => [a.name, a.value])
      ),
      href: card.querySelector("a[href]")?.getAttribute("href") || null,
      innerLinks: [...card.querySelectorAll("a[href]")].map((a) => a.getAttribute("href")).slice(0, 3),
      hasOnclick: !!card.onclick,
      cursor: getComputedStyle(card).cursor,
      text: (card.innerText || "").replace(/\s+/g, " ").slice(0, 100),
    };
    log("Première card trouvée :");
    console.log(info);

    // React fiber (state interne React)
    const fiberKey = Object.keys(card).find((k) => k.startsWith("__reactFiber") || k.startsWith("__reactInternalInstance"));
    if (fiberKey) {
      log("React fiber détecté → tente d'extraire les props...");
      const fiber = card[fiberKey];
      let node = fiber;
      let depth = 0;
      while (node && depth < 8) {
        if (node.memoizedProps) {
          const props = node.memoizedProps;
          const useful = Object.entries(props).filter(
            ([k, v]) => typeof v === "string" || typeof v === "number" || k === "to" || k === "href" || k === "matchId" || k === "id"
          );
          if (useful.length) {
            log(`  Profondeur ${depth} props utiles :`, Object.fromEntries(useful));
          }
        }
        node = node.return;
        depth++;
      }
    }

    // Tente un click programmatique pour voir le routing
    log("Pour capturer une URL : ouvre Network tab puis CLIQUE manuellement sur 1 match.");
    log("L'URL de la requête XHR ou la nouvelle URL du browser nous dira le pattern.");

    return info;
  }

  // Attache à window.wina (existant ou crée)
  if (!window.wina) window.wina = {};
  Object.assign(window.wina, {
    deep: runDeep,
    csvDeep: downloadCSVDeep,
    diagDeep,
    diagCard,
    scanUrls,
  });

  log("Ready. Workflow :");
  log("  wina.scanUrls()              // diag : combien d'URLs visibles dans le DOM");
  log("  await wina.deep({ max: 20 }) // capture marchés secondaires (auto-fallback DOM)");
  log("  wina.csvDeep()                // download deep CSV");
  log("  await wina.diagDeep('Bodø')   // tester 1 match précis");
})();
