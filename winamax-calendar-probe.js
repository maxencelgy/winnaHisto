// Probe DOM pour calendar Winamax — colle ça après wina.scan() qui a renvoyé 0
// Le but : trouver les bons sélecteurs (liens, data-testid, structure cards)
(() => {
  const log = (...a) => console.log("%c[probe]", "color:#fbbf24;font-weight:bold", ...a);

  // 1) Quels types de liens existent ?
  const allLinks = [...document.querySelectorAll("a[href]")];
  const hrefSamples = {};
  for (const a of allLinks) {
    const h = a.getAttribute("href") || "";
    const seg = h.split("/").slice(0, 4).join("/");
    hrefSamples[seg] = (hrefSamples[seg] || 0) + 1;
  }
  log("Top patterns href :");
  console.table(
    Object.entries(hrefSamples)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([k, v]) => ({ pattern: k, count: v })),
  );

  // 2) data-testid présents
  const testids = {};
  for (const el of document.querySelectorAll("[data-testid]")) {
    const t = el.getAttribute("data-testid").replace(/-?\d+/g, "*");
    testids[t] = (testids[t] || 0) + 1;
  }
  log("Top data-testid :");
  console.table(
    Object.entries(testids)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 25)
      .map(([k, v]) => ({ testid: k, count: v })),
  );

  // 3) Cherche les éléments qui contiennent "X.XX" ou "X,XX" (cotes)
  const oddsRe = /\b\d+[,.]\d{2}\b/;
  const candidates = [];
  for (const el of document.querySelectorAll("button, span, div")) {
    if (el.children.length > 0) continue; // feuilles uniquement
    const t = (el.textContent || "").trim();
    if (oddsRe.test(t) && t.length < 8) {
      candidates.push(el);
      if (candidates.length >= 5) break;
    }
  }
  log(`${candidates.length} feuilles ressemblant à des cotes.`);
  candidates.slice(0, 3).forEach((el, i) => {
    log(`Sample cote #${i + 1} :`, el.textContent.trim());
    let p = el;
    const path = [];
    for (let j = 0; j < 8 && p; j++) {
      const tag = p.tagName?.toLowerCase() || "?";
      const cls = p.className && typeof p.className === "string"
        ? "." + p.className.split(" ").slice(0, 2).join(".")
        : "";
      const id = p.dataset?.testid ? `[testid=${p.dataset.testid}]` : "";
      path.push(`${tag}${id}${cls.slice(0, 50)}`);
      p = p.parentElement;
    }
    console.log("  chemin :", path.join(" > "));
  });

  // 4) Texte d'une "section" probable (premier ancêtre qui contient ≥3 cotes)
  if (candidates[0]) {
    let p = candidates[0];
    for (let i = 0; i < 10 && p; i++) {
      const txt = p.textContent || "";
      const odds = (txt.match(/\b\d+[,.]\d{2}\b/g) || []).length;
      if (odds >= 3) {
        log("Card candidate :", {
          tag: p.tagName,
          testid: p.dataset?.testid,
          textPreview: txt.replace(/\s+/g, " ").slice(0, 200),
          oddsCount: odds,
          links: p.querySelectorAll("a[href]").length,
          hrefSample: p.querySelector("a[href]")?.getAttribute("href"),
        });
        break;
      }
      p = p.parentElement;
    }
  }

  // 5) Total : nb d'éléments avec cote pattern
  const total = document.body.textContent.match(/\b\d+[,.]\d{2}\b/g) || [];
  log(`Total occurrences cote dans la page : ${total.length}`);
  log(`URL courante : ${location.href}`);
})();
