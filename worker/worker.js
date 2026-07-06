// Cinema Atlas — Melde- und Vorschlags-Worker.
//
// Drei getrennte Wege:
//   1) POST /report    — freier Fehlerbericht (Kino fehlt, o.ä.) -> GitHub Issue (Label "user-report").
//                         Nur Information, keine automatische Übernahme.
//   2) POST /suggest    — strukturierter Änderungsvorschlag (Feld: bisher -> Vorschlag) von einem
//                         normalen Besucher -> GitHub Issue (Label "edit-suggestion"). Wird erst
//                         nach Admin-Bestätigung wirksam.
//   3) /admin/*         — nur mit korrektem "X-Admin-Key"-Header nutzbar:
//        GET  /admin/suggestions        Liste aller offenen Änderungsvorschläge
//        POST /admin/approve {number}   Vorschlag übernehmen -> schreibt corrections.json, schließt Issue
//        POST /admin/reject  {number}   Vorschlag ablehnen -> schließt Issue ohne Übernahme
//        POST /admin/patch {id,patch}   Admin trägt eine Änderung DIREKT ein (kein Issue, sofort wirksam)
//
// Benötigte Secrets/Variablen (siehe README.md):
//   GH_TOKEN   Fine-grained PAT für dieses Repo, Rechte "Issues: Read and write" + "Contents: Read and write"
//   GH_REPO    z. B. "final-wav/cinema-atlas"
//   ADMIN_KEY  frei gewähltes Admin-Passwort (Secret)

const MAX_LEN = 3000;
const PATCH_FIELDS = ["n", "ci", "co", "st", "url", "note", "lat", "lng"];
const FIELD_LABEL = { n: "Name", ci: "Stadt", co: "Land", st: "Bundesland/Region",
  url: "Website", note: "Hinweis", lat: "Breite (lat)", lng: "Länge (lng)" };

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Admin-Key",
    "Access-Control-Max-Age": "86400",
  };
}
function json(obj, status, origin) {
  return new Response(JSON.stringify(obj), {
    status, headers: { "Content-Type": "application/json", ...corsHeaders(origin) },
  });
}
function clean(s, max = MAX_LEN) { return (s || "").toString().trim().slice(0, max); }

function b64EncodeUtf8(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = ""; bytes.forEach((b) => (bin += String.fromCharCode(b)));
  return btoa(bin);
}
function b64DecodeUtf8(b64) {
  const bin = atob(b64.replace(/\n/g, ""));
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function requireAdmin(request, env) {
  const key = request.headers.get("X-Admin-Key") || "";
  return !!env.ADMIN_KEY && key === env.ADMIN_KEY;
}

async function gh(env, path, opts = {}) {
  const res = await fetch(`https://api.github.com${path}`, {
    ...opts,
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "cinema-atlas-worker",
      ...(opts.body ? { "Content-Type": "application/json" } : {}),
      ...(opts.headers || {}),
    },
  });
  return res;
}

function buildPatchBlock(id, cinema, city, original, patch) {
  const rows = PATCH_FIELDS.filter((k) => patch[k] !== undefined && patch[k] !== "")
    .map((k) => `| ${FIELD_LABEL[k]} | ${original[k] ?? "-"} | ${patch[k]} |`).join("\n");
  const table = rows
    ? `| Feld | Bisher | Vorschlag |\n|---|---|---|\n${rows}`
    : "_(keine Feldänderungen übermittelt)_";
  const data = { id, cinema, city, patch, original };
  return `**Kino:** ${cinema || "-"}\n**Stadt:** ${city || "-"}\n\n${table}\n\n` +
    "```json\n" + JSON.stringify(data) + "\n```\n\n---\n" +
    "_Automatisch übermittelt über das Änderungsformular von Cinema Atlas._";
}

function extractPatchBlock(issueBody) {
  const m = (issueBody || "").match(/```json\s*([\s\S]*?)```/);
  if (!m) return null;
  try { return JSON.parse(m[1]); } catch { return null; }
}

async function applyCorrection(env, id, patch) {
  const repo = env.GH_REPO;
  const filtered = {};
  for (const k of PATCH_FIELDS) if (patch[k] !== undefined && patch[k] !== "") filtered[k] = patch[k];

  const getRes = await gh(env, `/repos/${repo}/contents/corrections.json`);
  let sha, current = {};
  if (getRes.status === 200) {
    const j = await getRes.json();
    sha = j.sha;
    try { current = JSON.parse(b64DecodeUtf8(j.content)); } catch { current = {}; }
  } else if (getRes.status !== 404) {
    throw new Error(`corrections.json lesen fehlgeschlagen (${getRes.status})`);
  }

  current[id] = { ...(current[id] || {}), ...filtered };
  const body = {
    message: `Korrektur: ${id}`,
    content: b64EncodeUtf8(JSON.stringify(current, null, 2)),
    branch: "main",
  };
  if (sha) body.sha = sha;

  const putRes = await gh(env, `/repos/${repo}/contents/corrections.json`, {
    method: "PUT", body: JSON.stringify(body),
  });
  if (!putRes.ok) {
    const detail = await putRes.text().catch(() => "");
    throw new Error(`corrections.json schreiben fehlgeschlagen (${putRes.status}): ${detail.slice(0, 200)}`);
  }
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "*";
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(origin) });

    const { pathname } = new URL(request.url);
    const repo = env.GH_REPO || "final-wav/cinema-atlas";

    try {
      // ---------------- öffentlich: freier Fehlerbericht ----------------
      if (pathname === "/report") {
        if (request.method !== "POST") return json({ error: "method not allowed" }, 405, origin);
        const body = await request.json().catch(() => null);
        if (!body) return json({ error: "invalid json" }, 400, origin);
        if (clean(body.website)) return json({ ok: true }, 200, origin); // Honeypot

        const cinema = clean(body.cinema, 200), city = clean(body.city, 200);
        const kind = clean(body.kind, 50) || "sonstiges", message = clean(body.message, MAX_LEN);
        const contact = clean(body.contact, 200);
        if (!message) return json({ error: "message required" }, 400, origin);

        const kindLabel = { fehlt: "Kino fehlt komplett", standort: "Standort ist falsch",
          format: "Format/Ausstattung falsch oder fehlt", sonstiges: "Sonstiges" }[kind] || kind;
        const title = `Meldung: ${cinema || "(kein Name)"} ${city ? "(" + city + ")" : ""} — ${kindLabel}`.slice(0, 250);
        const issueBody = [`**Kino:** ${cinema || "-"}`, `**Stadt:** ${city || "-"}`, `**Art:** ${kindLabel}`,
          `**Kontakt:** ${contact || "-"}`, "", message, "", "---",
          "_Automatisch übermittelt über das Meldeformular von Cinema Atlas._"].join("\n");

        const ghRes = await gh(env, `/repos/${repo}/issues`, {
          method: "POST", body: JSON.stringify({ title, body: issueBody, labels: ["user-report"] }),
        });
        if (!ghRes.ok) return json({ error: "github error", status: ghRes.status }, 502, origin);
        return json({ ok: true }, 200, origin);
      }

      // ---------------- öffentlich: strukturierter Änderungsvorschlag ----------------
      if (pathname === "/suggest") {
        if (request.method !== "POST") return json({ error: "method not allowed" }, 405, origin);
        const body = await request.json().catch(() => null);
        if (!body) return json({ error: "invalid json" }, 400, origin);
        if (clean(body.website)) return json({ ok: true }, 200, origin); // Honeypot

        const id = clean(body.id, 50);
        const cinema = clean(body.cinema, 200), city = clean(body.city, 200);
        const patch = body.patch && typeof body.patch === "object" ? body.patch : {};
        const original = body.original && typeof body.original === "object" ? body.original : {};
        if (!id) return json({ error: "id required" }, 400, origin);

        const hasChange = PATCH_FIELDS.some((k) => patch[k] !== undefined && patch[k] !== "" && patch[k] !== original[k]);
        if (!hasChange) return json({ error: "no changes" }, 400, origin);

        const title = `Vorschlag: ${cinema || "(kein Name)"} ${city ? "(" + city + ")" : ""} — Änderung`.slice(0, 250);
        const issueBody = buildPatchBlock(id, cinema, city, original, patch);
        const ghRes = await gh(env, `/repos/${repo}/issues`, {
          method: "POST", body: JSON.stringify({ title, body: issueBody, labels: ["edit-suggestion"] }),
        });
        if (!ghRes.ok) return json({ error: "github error", status: ghRes.status }, 502, origin);
        return json({ ok: true }, 200, origin);
      }

      // ---------------- ab hier: nur Admin ----------------
      if (pathname.startsWith("/admin/")) {
        if (!requireAdmin(request, env)) return json({ error: "unauthorized" }, 401, origin);

        if (pathname === "/admin/suggestions" && request.method === "GET") {
          const listRes = await gh(env, `/repos/${repo}/issues?labels=edit-suggestion&state=open&per_page=50`);
          if (!listRes.ok) return json({ error: "github error", status: listRes.status }, 502, origin);
          const issues = await listRes.json();
          const items = issues.map((iss) => {
            const parsed = extractPatchBlock(iss.body) || {};
            return { number: iss.number, url: iss.html_url, created_at: iss.created_at,
              cinema: parsed.cinema || "", city: parsed.city || "", id: parsed.id || "",
              patch: parsed.patch || {}, original: parsed.original || {} };
          });
          return json({ ok: true, items }, 200, origin);
        }

        if (pathname === "/admin/approve" && request.method === "POST") {
          const body = await request.json().catch(() => null);
          const number = body && body.number;
          if (!number) return json({ error: "number required" }, 400, origin);

          const issRes = await gh(env, `/repos/${repo}/issues/${number}`);
          if (!issRes.ok) return json({ error: "issue not found" }, 404, origin);
          const issue = await issRes.json();
          const parsed = extractPatchBlock(issue.body);
          if (!parsed || !parsed.id) return json({ error: "kein gültiger Vorschlag in diesem Issue" }, 400, origin);

          await applyCorrection(env, parsed.id, parsed.patch || {});
          await gh(env, `/repos/${repo}/issues/${number}/comments`, {
            method: "POST", body: JSON.stringify({ body: "✅ Übernommen — Änderung ist jetzt live." }),
          });
          await gh(env, `/repos/${repo}/issues/${number}`, {
            method: "PATCH", body: JSON.stringify({ state: "closed" }),
          });
          return json({ ok: true }, 200, origin);
        }

        if (pathname === "/admin/reject" && request.method === "POST") {
          const body = await request.json().catch(() => null);
          const number = body && body.number;
          if (!number) return json({ error: "number required" }, 400, origin);
          const reason = clean(body.reason, 500);
          await gh(env, `/repos/${repo}/issues/${number}/comments`, {
            method: "POST", body: JSON.stringify({ body: "❌ Abgelehnt" + (reason ? `: ${reason}` : "") }),
          });
          await gh(env, `/repos/${repo}/issues/${number}`, {
            method: "PATCH", body: JSON.stringify({ state: "closed" }),
          });
          return json({ ok: true }, 200, origin);
        }

        if (pathname === "/admin/patch" && request.method === "POST") {
          const body = await request.json().catch(() => null);
          const id = body && clean(body.id, 50);
          const patch = body && body.patch && typeof body.patch === "object" ? body.patch : null;
          if (!id || !patch) return json({ error: "id und patch required" }, 400, origin);
          await applyCorrection(env, id, patch);
          return json({ ok: true }, 200, origin);
        }

        return json({ error: "not found" }, 404, origin);
      }

      return json({ ok: true, info: "Cinema Atlas Worker. POST /report, POST /suggest, /admin/*" }, 200, origin);
    } catch (err) {
      return json({ error: "internal error", detail: String(err).slice(0, 300) }, 500, origin);
    }
  },
};
