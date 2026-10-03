export const meta = {
  name: 'vinted-analyse',
  description: 'Analysiert neue Schuh-Ordner (Fotos) und erzeugt fertige Inserate für die Vinted Zentrale: englischer Text, Bestätigungsfragen, Preisvorschlag; danach kritische Gegenprüfung',
  whenToUse: 'Nachdem neue Fotos in schuhe/<NN_name>/ einsortiert wurden. args = [{ordner, fotos: [dateinamen]}]',
  phases: [
    { title: 'Analyse', detail: 'ein Agent pro Paar: Fotos lesen, Preis recherchieren, Inserat + Fragen schreiben, selbst prüfen' },
    { title: 'Gegenprüfung', detail: 'ein Agent pro Paar: Fakten widerlegen, Text/Fragen korrigieren, Prüfwerkzeug erneut' },
  ],
}

const ROOT = 'C:\\Users\\Patrick\\Documents\\Python\\VintedUploader'
const PY = ROOT + '\\.venv\\Scripts\\python.exe'
const PRUEF = `${PY} ${ROOT}\\werkzeuge\\pruefe_inserat.py`
const AUS = ROOT + '\\analyse'

const FORMAT = `
OUTPUT FILE FORMAT (one JSON object, UTF-8) — exactly the format of the "Vinted Zentrale" (for examples read ${ROOT}\\inserate.json and look at two existing entries that have "fragen" — other shoes, not yours; if it has none, use ${ROOT}\\_archiv\\*\\inserate_alt.json. IGNORE their "antwort"/"verlauf"/"status"/"geaendert"/"preis"/"vinted_*" values):
{
  "ordner": "<folder name>",
  "status": "neu",
  "titel": "<ENGLISH, max ~60 chars: Brand Type Colour key-feature Size NN — e.g. 'Vagabond Chelsea Boots Black Block Heel Lug Sole Size [?]'>",
  "beschreibung": "<BILINGUAL, \\n separated, no blank lines, max 2000 characters: first the ENGLISH block (5-9 short lines: what it is (brand/model), 'Size: NN', 'Material: …', 'Shape: …', 'Heel height: approx. X cm (estimated)', honest condition incl. flaws), then one line exactly '— Deutsch —', then the same content in natural GERMAN with the same line order ('Größe: NN', 'Material: …', 'Form: …', 'Absatzhöhe: ca. X cm (geschätzt)', 'Zustand: …'), last line 3-4 hashtags without umlauts>",
  "kategorie": "<Vinted path, English, separated by ' > '>",
  "marke": "<brand or 'unbekannt'>", "groesse": "<EU size read on the shoe, else 'unbekannt'>",
  "zustand": "Neu mit Etikett" | "Neu ohne Etikett" | "Sehr gut" | "Gut" | "Zufriedenstellend",
  "farbe": "<max 2 German colour names from: Schwarz, Grau, Weiß, Creme, Beige, Orange, Rot, Bordeaux, Pink, Rosa, Lila, Blau, Navy, Türkis, Grün, Khaki, Gelb, Gold, Silber, Braun, Mehrfarbig — comma separated>",
  "material": "<one of Leder, Wildleder, Kunstleder, Canvas, Gummi, Jute — only if sure; '' if unsure (then ask a question)>",
  "absatzhoehe": "<English, e.g. 'Block heel approx. 7 cm (estimated)' or 'Flat, sole approx. 3 cm (estimated)'>",
  "schuhform": "<English short shape: type, toe, heel type, shaft height, closure>",
  "paket": "Klein" | "Mittel" | "Groß",
  "preis": null, "preis_min": null,
  "preis_vorschlag": <number EUR>, "preis_min_vorschlag": <number EUR>,
  "preis_begruendung": "<German, 1-2 sentences with the key price facts>",
  "hinweise": ["<German, max 6 short to-dos for the seller: photos to take, things to measure. NEVER tell the seller to edit text or delete placeholders — questions do that>"],
  "fotos": ["<file names in best order: cover = whole pair side view first, sole/labels later>"],
  "fragen": [ <question objects, see QUESTIONS> ],
  "verlauf": [],
  "notiz": "",
  "analyse": {"marke_beleg": "<German: which photo, what text/logo you saw — no crop file names>", "groesse_beleg": "…", "zustand_begruendung": "…",
              "maengel": ["…"], "form_beleg": "<how heel height/shape were measured>", "modell": "<or ''>", "geschlecht": "Damen|Herren|Unisex|unklar", "preis_quellen": ["<urls>"]}
}

VINTED CATEGORIES (English UI of vinted.lu, verified for women):
Women > Shoes > {Ballerinas | Boat shoes, loafers & moccasins | Clogs & mules | Espadrilles | Flip-flops & slides | Heels | Lace-up shoes | Mary Janes & T-bar shoes | Sandals | Slippers | Trainers}
Women > Shoes > Boots > {Ankle boots | Mid-calf boots | Knee-high boots | Over-the-knee boots | Snow boots | Wellington boots | Work boots}
Women > Shoes > Sports shoes > … (sub-levels not verified)
Men > Shoes > … (not verified; use the closest analogous English name, e.g. 'Men > Shoes > Trainers', 'Men > Shoes > Boots')
Chelsea boots → Women > Shoes > Boots > Ankle boots.

QUESTIONS — the seller never edits the description by hand. Every uncertain fact is written into the text with a marker AND gets a question whose options rewrite the text:
- Marker styles: English block '[? please confirm]' right after an uncertain claim (e.g. 'by Vagabond [? please confirm]'), '[?]' for an unknown value (e.g. 'Size: [?]', 'Box/tags: [?]'); German block '[? bitte bestätigen]' / '[?]' (e.g. 'von Vagabond [? bitte bestätigen]', 'Größe: [?]').
- The description is bilingual, so every uncertain fact appears TWICE: every option must contain replacement pairs for the English AND the German occurrence.
- Question object: {"id": "<short id>", "feld": "<field it resolves, optional: marke|groesse|material|kategorie|zustand>", "frage": "<German question>", "erklaerung": "<German, why unsure, short>",
   "optionen": [{"label": "<German button text>", "ersetzen": [["<exact old text>", "<new text>"], ["<old>", "<new>", true]], "felder": {"<field>": "<value>"}},
                {"label": "Größe", "eingabe": true, "platzhalter": "z. B. 39", "knopf": "Übernehmen", "ersetzen": [["Size: [?]", "Size: {wert}"], ["Größe: [?]", "Größe: {wert}"], ["Size [?]", "Size {wert}"]], "felder": {"groesse": "{wert}"}}]}
  * "ersetzen" pairs are applied to BOTH titel and beschreibung; "{wert}" = the seller's typed input; a third element true = optional (e.g. hashtags that may not exist).
  * The FIRST pair of every option must literally occur in titel or beschreibung. Pairs that delete text must take the newline or the leading space/separator with them so no blank line, double space or ' ,' remains.
  * Standard questions: unknown size (id "groesse", see above, field groesse = 'unbekannt'); likely-but-unconfirmed brand X: options "Ja, X" / "Andere Marke" (eingabe, also rewrites the title part and removes the brand hashtag) / "Ohne Marke / unbekannt" (removes ' by X [? please confirm]' or similar, rewrites title to e.g. "Women's …", felder marke 'Ohne Marke'); unknown brand: text line 'Brand: [?]' with options eingabe / "Ohne Marke / unbekannt" (deletes the line); uncertain material: 'probably smooth leather [?]' with options "Ja, echt" / "Nein, Kunstleder" / "Weiß nicht" (keeps 'probably …' without marker), setting felder material accordingly ('' when unsure); optional facts (box, inside zip, outsole not photographed: 'Outsole: [?]'): options that fill in or delete the fact; gender unclear for unisex trainers: question id "kategorie" with options setting felder kategorie.
  * After answering every question with its FIRST option, no '[?' may remain anywhere. No '[?' without a question.
  * Do not ask about things that are clearly visible.

RULES: Never invent facts (no 'worn twice', 'smoke-free home', 'original box' unless visible). Brand only from readable text/logo. Size only from a number you actually read. Heel height = an estimate, always 'approx. … (estimated)'. All seller-facing German texts must be short and plain.`

function analysePrompt(p) {
  return `You create ONE finished Vinted listing for a private seller in Luxembourg (vinted.lu, English listing text, German UI for the seller). Today: see system date. Photos of ONE pair of shoes: ${ROOT}\\schuhe\\${p.ordner}\\ — files: ${p.fotos.join(', ')}.

STEPS
1. Look at every photo. Photos may be HEIC/JPG with EXIF rotation: open them with Python (${PY}) via "import sys; sys.path.insert(0, r'${ROOT}'); import vinted; im = vinted.oeffne_bild(path)" (handles HEIC + rotation), save downscaled JPG copies or zoomed crops to ${AUS}\\_crops\\${p.ordner}\\ and Read those. Zoom into insole, tongue, heel, outsole and shaft labels to read brand, size, material, model. Use a pixel grid on a side view to estimate heel/platform height relative to shoe length (outsole ≈ size × 0.667 cm + 1 cm; if size unknown assume EU 39 → ~27 cm and say so).
2. Assess condition honestly (outsole wear, creases, scuffs, dirt) → zustand.
3. Price research: load WebSearch/WebFetch via ToolSearch ("select:WebSearch,WebFetch"). Retail price + what similar used items sell for on Vinted/eBay/Kleinanzeigen (FR/BE/LU/DE). Be realistic for Vinted (used shoes sell well below retail; Vinted's own recommendation for a branded espadrille in very good condition was only 7/11/14 €). preis_vorschlag = realistic asking price, preis_min_vorschlag ≈ 75-80 % of it.
4. Write the listing JSON to ${AUS}\\${p.ordner}.json (create the folder). Then run: ${PRUEF} ${AUS}\\${p.ordner}.json — fix and re-run until it prints OK.
${FORMAT}

Return a short German summary (brand, size, condition, price suggestion, number of questions, and the final line of the checker output).`
}

function pruefPrompt(p, zusammenfassung) {
  return `You are an adversarial reviewer of a generated Vinted listing. File: ${AUS}\\${p.ordner}.json. Photos: ${ROOT}\\schuhe\\${p.ordner}\\ (${p.fotos.join(', ')}). Open photos via Python: "import sys; sys.path.insert(0, r'${ROOT}'); import vinted; vinted.oeffne_bild(path)", save crops to ${AUS}\\_crops\\${p.ordner}\\ and Read them.

Previous agent's summary: ${zusammenfassung}

Try to REFUTE each factual claim with your own crops: brand (readable?), size (actually printed?), model, material, condition grade vs. visible wear, every flaw/positive claim in the description, heel height plausibility, category choice. Anything not supported must become uncertain (marker + question) or be removed; anything clearly visible that is asked as a question should be stated instead. Also check the English is natural, the title is searchable, the German questions are clear, the price suggestion is realistic for Vinted.
Edit the file directly if needed, keeping the format below, then run ${PRUEF} ${AUS}\\${p.ordner}.json until it prints OK.
${FORMAT}

Return a short German report: what you changed (or "keine Änderungen") and the final checker line.`
}

const ergebnisse = await pipeline(
  args,
  p => agent(analysePrompt(p), { label: `analyse:${p.ordner}`, phase: 'Analyse' }),
  (zus, p) => agent(pruefPrompt(p, zus || '(keine Zusammenfassung)'), { label: `pruefen:${p.ordner}`, phase: 'Gegenprüfung' })
    .then(bericht => ({ ordner: p.ordner, analyse: zus, pruefung: bericht })),
)
return ergebnisse.filter(Boolean)
