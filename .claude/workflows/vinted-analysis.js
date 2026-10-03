export const meta = {
  name: 'vinted-analysis',
  description: 'Analysiert neue Schuh-Ordner (Fotos) und erzeugt fertige Inserate für die Vinted Zentrale: englischer Text, Bestätigungsfragen, Preisvorschlag; danach kritische Gegenprüfung',
  whenToUse: 'Nachdem neue Fotos in data/items/<NN_name>/ einsortiert wurden. args = [{folder, photos: [dateinamen]}]',
  phases: [
    { title: 'Analyse', detail: 'ein Agent pro Paar: Fotos lesen, Preis recherchieren, Inserat + Fragen schreiben, selbst prüfen' },
    { title: 'Gegenprüfung', detail: 'ein Agent pro Paar: Fakten widerlegen, Text/Fragen korrigieren, Prüfwerkzeug erneut' },
  ],
}

const ROOT = 'C:\\Users\\Patrick\\Documents\\Python\\VintedUploader'
const PY = ROOT + '\\.venv\\Scripts\\python.exe'
const CHECK = `${PY} ${ROOT}\\tools\\check_listing.py`
const DATA = ROOT + '\\data'
const OUT = DATA + '\\analysis'

const FORMAT = `
OUTPUT FILE FORMAT (one JSON object, UTF-8) — exactly the format of the Vinted hub (for examples read ${DATA}\\listings.json and look at two existing entries that have "questions" — other shoes, not yours; if it has none, use ${DATA}\\archive\\*\\listings_old.json. IGNORE their "answer"/"history"/"status"/"updated_at"/"price"/"vinted_*" values; keys and values must follow the format below):
{
  "folder": "<folder name>",
  "status": "new",
  "title": "<ENGLISH, max ~60 chars: Brand Type Colour key-feature Size NN — e.g. 'Vagabond Chelsea Boots Black Block Heel Lug Sole Size [?]'>",
  "description": "<BILINGUAL, \\n separated, no blank lines, max 2000 characters: first the ENGLISH block (5-9 short lines: what it is (brand/model), 'Size: NN', 'Material: …', 'Shape: …', 'Heel height: approx. X cm (estimated)', honest condition incl. flaws), then one line exactly '— Deutsch —', then the same content in natural GERMAN with the same line order ('Größe: NN', 'Material: …', 'Form: …', 'Absatzhöhe: ca. X cm (geschätzt)', 'Zustand: …'), last line 3-4 hashtags without umlauts>",
  "category": "<Vinted path, English, separated by ' > '>",
  "brand": "<brand or 'unknown'>", "size": "<EU size read on the shoe, else 'unknown'>",
  "condition": "New with tags" | "New without tags" | "Very good" | "Good" | "Satisfactory",
  "color": "<max 2 English Vinted colour names from: Black, Grey, White, Cream, Beige, Orange, Red, Burgundy, Pink, Purple, Blue, Navy, Turquoise, Green, Khaki, Yellow, Gold, Silver, Brown, Multi — comma separated>",
  "material": "<one of Leather, Suede, Faux leather, Canvas, Rubber, Jute — only if sure; '' if unsure (then ask a question)>",
  "heel_height": "<English, e.g. 'Block heel approx. 7 cm (estimated)' or 'Flat, sole approx. 3 cm (estimated)'>",
  "shape": "<English short shape: type, toe, heel type, shaft height, closure>",
  "package": "Small" | "Medium" | "Large",
  "price": null, "min_price": null,
  "suggested_price": <number EUR>, "suggested_min_price": <number EUR>,
  "price_reasoning": "<German, 1-2 sentences with the key price facts>",
  "hints": ["<German, max 6 short to-dos for the seller: photos to take, things to measure. NEVER tell the seller to edit text or delete placeholders — questions do that>"],
  "photos": ["<file names in best order: cover = whole pair side view first, sole/labels later>"],
  "questions": [ <question objects, see QUESTIONS> ],
  "history": [],
  "notes": "",
  "analysis": {"brand_evidence": "<German: which photo, what text/logo you saw — no crop file names>", "size_evidence": "…", "condition_reasoning": "…",
               "flaws": ["…"], "shape_evidence": "<how heel height/shape were measured>", "model": "<or ''>", "gender": "women|men|unisex|unclear", "price_sources": ["<urls>"]}
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
- Question object: {"id": "<short id>", "field": "<field it resolves, optional: brand|size|material|category|condition>", "question": "<German question>", "explanation": "<German, why unsure, short>",
   "options": [{"label": "<German button text>", "replace": [["<exact old text>", "<new text>"], ["<old>", "<new>", true]], "fields": {"<field>": "<value>"}},
               {"label": "Größe", "input": true, "placeholder": "z. B. 39", "button": "Übernehmen", "replace": [["Size: [?]", "Size: {value}"], ["Größe: [?]", "Größe: {value}"], ["Size [?]", "Size {value}"]], "fields": {"size": "{value}"}}]}
  * "replace" pairs are applied to BOTH title and description; "{value}" = the seller's typed input; a third element true = optional (e.g. hashtags that may not exist).
  * The FIRST pair of every option must literally occur in title or description. Pairs that delete text must take the newline or the leading space/separator with them so no blank line, double space or ' ,' remains.
  * "fields" use the listing keys and values of the format above (e.g. {"brand": "No brand"}, {"condition": "New without tags"}, {"material": "Faux leather"}).
  * Standard questions: unknown size (id "size", see above, field size = 'unknown'); likely-but-unconfirmed brand X: options "Ja, X" / "Andere Marke" (input, also rewrites the title part and removes the brand hashtag) / "Ohne Marke / unbekannt" (removes ' by X [? please confirm]' or similar, rewrites title to e.g. "Women's …", fields brand 'No brand'); unknown brand: text line 'Brand: [?]' with options input / "Ohne Marke / unbekannt" (deletes the line); uncertain material: 'probably smooth leather [?]' with options "Ja, echt" / "Nein, Kunstleder" / "Weiß nicht" (keeps 'probably …' without marker), setting fields material accordingly ('' when unsure); optional facts (box, inside zip, outsole not photographed: 'Outsole: [?]'): options that fill in or delete the fact; gender unclear for unisex trainers: question id "category" with options setting fields category.
  * After answering every question with its FIRST option, no '[?' may remain anywhere. No '[?' without a question.
  * Do not ask about things that are clearly visible.

RULES: Never invent facts (no 'worn twice', 'smoke-free home', 'original box' unless visible). Brand only from readable text/logo. Size only from a number you actually read. Heel height = an estimate, always 'approx. … (estimated)'. All seller-facing German texts must be short and plain.`

function analysisPrompt(p) {
  return `You create ONE finished Vinted listing for a private seller in Luxembourg (vinted.lu, English title, bilingual English + German description, German UI for the seller). Today: see system date. Photos of ONE pair of shoes: ${DATA}\\items\\${p.folder}\\ — files: ${p.photos.join(', ')}.

STEPS
1. Look at every photo. Photos may be HEIC/JPG with EXIF rotation: open them with Python (${PY}) via "import sys; sys.path.insert(0, r'${ROOT}'); from vinted_hub.core import open_image; im = open_image(path)" (handles HEIC + rotation), save downscaled JPG copies or zoomed crops to ${OUT}\\_crops\\${p.folder}\\ and Read those. Zoom into insole, tongue, heel, outsole and shaft labels to read brand, size, material, model. Use a pixel grid on a side view to estimate heel/platform height relative to shoe length (outsole ≈ size × 0.667 cm + 1 cm; if size unknown assume EU 39 → ~27 cm and say so).
2. Assess condition honestly (outsole wear, creases, scuffs, dirt) → condition.
3. Price research: load WebSearch/WebFetch via ToolSearch ("select:WebSearch,WebFetch"). Retail price + what similar used items sell for on Vinted/eBay/Kleinanzeigen (FR/BE/LU/DE). Be realistic for Vinted (used shoes sell well below retail; Vinted's own recommendation for a branded espadrille in very good condition was only 7/11/14 €). suggested_price = realistic asking price, suggested_min_price ≈ 75-80 % of it.
4. Write the listing JSON to ${OUT}\\${p.folder}.json (create the folder). Then run: ${CHECK} ${OUT}\\${p.folder}.json — fix and re-run until it prints OK.
${FORMAT}

Return a short German summary (brand, size, condition, price suggestion, number of questions, and the final line of the checker output).`
}

function reviewPrompt(p, summary) {
  return `You are an adversarial reviewer of a generated Vinted listing. File: ${OUT}\\${p.folder}.json. Photos: ${DATA}\\items\\${p.folder}\\ (${p.photos.join(', ')}). Open photos via Python: "import sys; sys.path.insert(0, r'${ROOT}'); from vinted_hub.core import open_image; open_image(path)", save crops to ${OUT}\\_crops\\${p.folder}\\ and Read them.

Previous agent's summary: ${summary}

Try to REFUTE each factual claim with your own crops: brand (readable?), size (actually printed?), model, material, condition grade vs. visible wear, every flaw/positive claim in the description, heel height plausibility, category choice. Anything not supported must become uncertain (marker + question) or be removed; anything clearly visible that is asked as a question should be stated instead. Also check the English is natural, the title is searchable, the German questions are clear, the price suggestion is realistic for Vinted.
Edit the file directly if needed, keeping the format below, then run ${CHECK} ${OUT}\\${p.folder}.json until it prints OK.
${FORMAT}

Return a short German report: what you changed (or "keine Änderungen") and the final checker line.`
}

const results = await pipeline(
  args,
  p => agent(analysisPrompt(p), { label: `analysis:${p.folder}`, phase: 'Analyse' }),
  (summary, p) => agent(reviewPrompt(p, summary || '(no summary)'), { label: `review:${p.folder}`, phase: 'Gegenprüfung' })
    .then(report => ({ folder: p.folder, analysis: summary, review: report })),
)
return results.filter(Boolean)
