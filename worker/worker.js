// Cinema Atlas — Melde-Worker.
// Nimmt Nutzer-Meldungen ("Kino fehlt" / "Standort falsch" / ...) vom Frontend entgegen
// und legt daraus ein GitHub Issue im Repo an. Es wird NICHTS automatisch in die
// Daten übernommen — der Repo-Besitzer sieht das Issue und pflegt es von Hand ein.
//
// Benötigtes Secret: GH_TOKEN
//   Fine-grained Personal Access Token, NUR für dieses eine Repo, NUR Berechtigung
//   "Issues: Read and write". Siehe README.md in diesem Ordner.
//
// Benötigte Variable: GH_REPO (z.B. "final-wav/cinema-atlas")

const MAX_LEN = 3000;

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

function json(obj, status, origin) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders(origin) },
  });
}

function clean(s, max = MAX_LEN) {
  return (s || "").toString().trim().slice(0, max);
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "*";

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    const url = new URL(request.url);
    if (url.pathname !== "/report") {
      return json({ ok: true, info: "Cinema Atlas Melde-Worker. POST /report" }, 200, origin);
    }
    if (request.method !== "POST") {
      return json({ error: "method not allowed" }, 405, origin);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "invalid json" }, 400, origin);
    }

    // Honeypot: verstecktes Feld, das nur Bots ausfüllen. Wenn befüllt -> so tun als
    // wäre alles ok, aber nichts anlegen.
    if (clean(body.website)) {
      return json({ ok: true }, 200, origin);
    }

    const cinema = clean(body.cinema, 200);
    const city = clean(body.city, 200);
    const kind = clean(body.kind, 50) || "sonstiges";
    const message = clean(body.message, MAX_LEN);
    const contact = clean(body.contact, 200);

    if (!message) {
      return json({ error: "message required" }, 400, origin);
    }

    const kindLabel = {
      fehlt: "Kino fehlt komplett",
      standort: "Standort ist falsch",
      format: "Format/Ausstattung falsch oder fehlt",
      sonstiges: "Sonstiges",
    }[kind] || kind;

    const title = `Meldung: ${cinema || "(kein Name)"} ${city ? "(" + city + ")" : ""} — ${kindLabel}`.slice(0, 250);
    const issueBody = [
      `**Kino:** ${cinema || "-"}`,
      `**Stadt:** ${city || "-"}`,
      `**Art:** ${kindLabel}`,
      `**Kontakt:** ${contact || "-"}`,
      "",
      message,
      "",
      "---",
      "_Automatisch übermittelt über das Meldeformular von Cinema Atlas._",
    ].join("\n");

    const repo = env.GH_REPO || "final-wav/cinema-atlas";
    const ghRes = await fetch(`https://api.github.com/repos/${repo}/issues`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GH_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "cinema-atlas-report-worker",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title, body: issueBody, labels: ["user-report"] }),
    });

    if (!ghRes.ok) {
      const detail = await ghRes.text().catch(() => "");
      return json({ error: "github error", status: ghRes.status, detail: detail.slice(0, 300) }, 502, origin);
    }

    return json({ ok: true }, 200, origin);
  },
};
