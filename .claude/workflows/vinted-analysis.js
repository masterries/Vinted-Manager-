export const meta = {
  name: 'vinted-analysis',
  description: 'Analysiert neue Schuh-Ordner (Fotos) und erzeugt fertige Inserate für die Vinted Zentrale: Titel und Beschreibung in der eingestellten Sprache (Beschreibung immer nur eine Sprache), Bestätigungsfragen, Preisvorschlag; danach kritische Gegenprüfung',
  whenToUse: 'Nachdem neue Fotos in data/items/<NN_name>/ einsortiert wurden. args = {settings: <Ausgabe von "python -m vinted_hub settings">, items: [{folder, photos: [dateinamen]}]}; die alte Form [{folder, photos}] gilt als Oberfläche de, Titel en, Beschreibung en; unbekannte Einstellungs-Schlüssel brechen ab. Ergebnis je Paar: {folder, settings (die verwendeten Sprachen), analysis, review}',
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

// ---- Languages -------------------------------------------------------------------------------
// title_language → title, description_language → description (one language only),
// ui_language → everything the seller reads in the hub, data values → always English.
const LANGS = ['en', 'de']
const LANG_NAME = { en: 'English', de: 'German' }
const DEFAULT_SETTINGS = { ui_language: 'de', title_language: 'en', description_language: 'en' }

// args: [{folder, photos}] (old form) or {settings: {ui_language, title_language, description_language}, items: [...]}
function readArgs(raw) {
  const a = typeof raw === 'string' ? JSON.parse(raw) : raw
  const items = Array.isArray(a) ? a : (a && Array.isArray(a.items) ? a.items : null)
  if (!items) throw new Error('args: expected [{folder, photos}] or {settings, items: [{folder, photos}]}')
  for (const p of items) {
    if (!p || !p.folder || !Array.isArray(p.photos) || !p.photos.length) throw new Error(`args: item needs folder and photos: ${JSON.stringify(p)}`)
  }
  let given = (!Array.isArray(a) && a.settings) || {}
  if (typeof given === 'string') given = JSON.parse(given)  // the settings line pasted as text
  if (typeof given !== 'object' || given === null || Array.isArray(given)) {
    throw new Error(`args.settings: expected an object like {"ui_language": "de", "title_language": "en", "description_language": "en"}, got ${JSON.stringify(given)}`)
  }
  const unknown = Object.keys(given).filter(k => !(k in DEFAULT_SETTINGS))
  if (unknown.length) throw new Error(`args.settings: unknown key(s) ${unknown.join(', ')} (allowed: ${Object.keys(DEFAULT_SETTINGS).join(', ')})`)
  const settings = {}
  for (const key of Object.keys(DEFAULT_SETTINGS)) {
    const v = given[key]
    if (v === undefined || v === null || v === '') settings[key] = DEFAULT_SETTINGS[key]
    else if (LANGS.includes(v)) settings[key] = v
    else throw new Error(`args.settings.${key} = ${JSON.stringify(v)} is not one of ${LANGS.join(', ')}`)
  }
  return { settings, items }
}

// Listing text (title / description) in each language
const TEXT = {
  en: {
    titlePattern: "Brand Type Colour key-feature Size NN — e.g. 'Vagabond Chelsea Boots Black Block Heel Lug Sole Size 39'",
    titleSize: 'Size',
    noBrandTitle: "Women's …",
    lines: "(1) intro: ONE sentence — brand/model (if known), type, colour, 1-2 key features, e.g. 'Black Chelsea boots by Vagabond with a block heel and lug sole.' (2) 2-4 fact lines: 'Size: NN', 'Material: …', 'Heel height: approx. X cm' (flats: leave out or 'Sole: approx. X cm'), optionally one more line only if it matters to a buyer (e.g. 'Comes with the original box.') (3) ONE short condition sentence matching the condition field, e.g. 'New with tags.' / 'New, never worn.' / 'Very good condition.' / 'Good condition.'",
    example: 'Black Chelsea boots by Vagabond with a block heel and lug sole.\\n\\nSize: 39\\nMaterial: leather\\nHeel height: approx. 6 cm\\n\\nVery good condition.\\n\\n#chelseaboots #blockheel #blackboots',
    hashtags: "3-4 English hashtags, e.g. '#chelseaboots #blockheel #blackboots'",
    sizeLine: 'Size: ', brandLine: 'Brand: ', boxLine: 'Box/tags: ', outsoleLine: 'Outsole: ',
    confirm: '[? please confirm]', by: 'by',
    probably: 'probably smooth leather', real: 'smooth leather', faux: 'faux leather',
    estimate: "'approx. …'",
    noWear: 'no signs of wear', newWord: 'new', wornBriefly: 'worn briefly',
    wear: {
      text: 'never worn [? please confirm], no signs of wear on the outsoles',
      yes: 'never worn, no signs of wear on the outsoles',
      tried: 'only tried on at home, no signs of wear on the outsoles',
      brief: 'worn briefly, only light signs of wear on the outsoles',
    },
  },
  de: {
    titlePattern: "Brand Type Colour key-feature Gr. NN, in German words — e.g. 'Vagabond Chelsea Boots Schwarz Blockabsatz Gr. 39'",
    titleSize: 'Gr.',
    noBrandTitle: 'Damen …',
    lines: "(1) intro: ONE sentence — brand/model (if known), type, colour, 1-2 key features, e.g. 'Schwarze Chelsea Boots von Vagabond mit Blockabsatz und Profilsohle.' (2) 2-4 fact lines: 'Größe: NN', 'Material: …', 'Absatzhöhe: ca. X cm' (flache Schuhe: weglassen oder 'Sohle: ca. X cm'), optionally one more line only if it matters to a buyer (e.g. 'Mit Originalkarton.') (3) ONE short condition sentence matching the condition field, e.g. 'Neu mit Etikett.' / 'Neu, nie getragen.' / 'Sehr guter Zustand.' / 'Guter Zustand.'",
    example: 'Schwarze Chelsea Boots von Vagabond mit Blockabsatz und Profilsohle.\\n\\nGröße: 39\\nMaterial: Leder\\nAbsatzhöhe: ca. 6 cm\\n\\nSehr guter Zustand.\\n\\n#chelseaboots #blockabsatz #schwarz',
    hashtags: "3-4 German hashtags without umlauts (ae/oe/ue/ss), e.g. '#stiefeletten #blockabsatz #schwarz'",
    sizeLine: 'Größe: ', brandLine: 'Marke: ', boxLine: 'Karton/Etikett: ', outsoleLine: 'Laufsohle: ',
    confirm: '[? bitte bestätigen]', by: 'von',
    probably: 'vermutlich Glattleder', real: 'Glattleder', faux: 'Kunstleder',
    estimate: "'ca. …'",
    noWear: 'keine Gebrauchsspuren', newWord: 'neu', wornBriefly: 'kurz getragen',
    wear: {
      text: 'nie getragen [? bitte bestätigen], keine Gebrauchsspuren an den Laufsohlen',
      yes: 'nie getragen, keine Gebrauchsspuren an den Laufsohlen',
      tried: 'nur zu Hause anprobiert, keine Gebrauchsspuren an den Laufsohlen',
      brief: 'kurz getragen, nur leichte Gebrauchsspuren an den Laufsohlen',
    },
  },
}

// Seller-facing texts (question buttons etc.) in each UI language
const UI = {
  de: {
    sizeLabel: 'Größe', sizePlaceholder: 'z. B. 39', apply: 'Übernehmen',
    yesBrand: 'Ja, X', otherBrand: 'Andere Marke', noBrand: 'Ohne Marke / unbekannt', brandLabel: 'Marke', brandPlaceholder: 'z. B. Tamaris',
    matYes: 'Ja, echt', matNo: 'Nein, Kunstleder', matUnsure: 'Weiß nicht',
    wearYes: 'Ja, nie getragen', wearTried: 'Nur anprobiert', wearBrief: 'Kurz getragen',
    noChanges: 'keine Änderungen',
  },
  en: {
    sizeLabel: 'Size', sizePlaceholder: 'e.g. 39', apply: 'Apply',
    yesBrand: 'Yes, X', otherBrand: 'Other brand', noBrand: 'No brand / unknown', brandLabel: 'Brand', brandPlaceholder: 'e.g. Tamaris',
    matYes: 'Yes, real leather', matNo: 'No, faux leather', matUnsure: 'Not sure',
    wearYes: 'Yes, never worn', wearTried: 'Only tried on', wearBrief: 'Worn briefly',
    noChanges: 'no changes',
  },
}

// The one place that states which text is written in which language
function languageRules(s) {
  const tl = LANG_NAME[s.title_language], dl = LANG_NAME[s.description_language], ul = LANG_NAME[s.ui_language]
  const germanText = s.title_language === 'de' || s.description_language === 'de'
  return `LANGUAGES FOR THIS LISTING — the only language rule; it overrides the language of any example you read:
- Title → ${tl}.
- Description → ${dl} only: every line, every marker, the hashtags and every replace text that changes the description. No block, line or translation in any other language, no separator line such as '— Deutsch —' / '— English —'.
- Seller-facing texts → ${ul}: question, explanation, label, placeholder, button, hints, price_reasoning, analysis.* (brand_evidence, size_evidence, condition_reasoning, flaws, shape_evidence) and the summary/report you return.
- Data values → English in every case: category path, brand (incl. 'No brand' / 'unknown'), size (incl. 'unknown'), condition, color, material, heel_height, shape, package, analysis.gender and every value inside "fields".${germanText ? `
- German title/description text uses German words for colours and materials (e.g. 'Schwarz', 'Wildleder'); the fields keep Vinted's English names (e.g. "color": "Black", "material": "Suede"). An English model or colourway name stays as it is (e.g. 'Smooth Leather', 'Triple White') and goes into analysis.model; in a German title it is fine as such, in a German description put it in German quotes („Puma Suede Classic“) — the checker skips quoted text and analysis.model but rejects other English words such as leather, suede, with, the.` : ''}
- Write "title_language": "${s.title_language}" and "description_language": "${s.description_language}" into the JSON.`
}

function format(s) {
  const T = TEXT[s.title_language], D = TEXT[s.description_language], U = UI[s.ui_language]
  const tl = LANG_NAME[s.title_language], dl = LANG_NAME[s.description_language], ul = LANG_NAME[s.ui_language]
  const sameReplaceLang = s.title_language === s.description_language
  return `
OUTPUT FILE FORMAT (one JSON object, UTF-8) — exactly the format of the Vinted hub (for examples read ${DATA}\\listings.json and look at two existing entries that have "questions" — other shoes, not yours; if it has none, use ${DATA}\\archive\\*\\listings_old.json. IGNORE their "answer"/"history"/"status"/"updated_at"/"price"/"vinted_*" values and the language of their texts; keys and values must follow the format below and the languages above):
{
  "folder": "<folder name>",
  "status": "new",
  "title_language": "${s.title_language}",
  "description_language": "${s.description_language}",
  "title": "<${tl.toUpperCase()}, max ~60 chars: ${T.titlePattern}; unknown size: '${T.titleSize} [?]'>",
  "description": "<${dl.toUpperCase()} ONLY, SHORT (about 150-400 characters, max 700) and friendly, blocks separated by exactly ONE blank line (\\n\\n — looks better on Vinted; no other blank lines): ${D.lines}; (4) last line ${D.hashtags}. Example: '${D.example}'>",
  "category": "<Vinted path, English, separated by ' > '>",
  "brand": "<brand or 'unknown'>", "size": "<EU size read on the shoe, else 'unknown'>",
  "condition": "New with tags" | "New without tags" | "Very good" | "Good" | "Satisfactory",
  "color": "<max 2 English Vinted colour names from: Black, Grey, White, Cream, Beige, Orange, Red, Burgundy, Pink, Purple, Blue, Navy, Turquoise, Green, Khaki, Yellow, Gold, Silver, Brown, Multi — comma separated>",
  "material": "<one of Leather, Suede, Faux leather, Canvas, Rubber, Jute — only if sure; '' if unsure (then ask a question)>",
  "heel_height": "<English, e.g. 'Block heel approx. 7 cm (estimated)' or 'Flat, sole approx. 3 cm (estimated)'>",
  "shape": "<English short shape: type, toe, heel type, shaft height, closure>",
  "package": "Medium" (default for shoes — the fill script selects it in Vinted's shipping section) | "Large" (ONLY for really big shoes: knee-high or over-the-knee boots, big snow/wellington boots, very large men's boots); never "Small",
  "price": null, "min_price": null,
  "suggested_price": <number EUR>, "suggested_min_price": <number EUR>,
  "price_reasoning": "<${ul}, 1-2 sentences with the key price facts>",
  "hints": ["<${ul}, max 6 short to-dos for the seller: photos to take, things to measure. NEVER tell the seller to edit text or delete placeholders — questions do that>"],
  "photos": ["<file names in best order: cover = whole pair side view first, sole/labels later>"],
  "questions": [ <question objects, see QUESTIONS> ],
  "history": [],
  "notes": "",
  "analysis": {"brand_evidence": "<${ul}: which photo, what text/logo you saw — no crop file names>", "size_evidence": "…", "condition_reasoning": "…",
               "flaws": ["…"], "shape_evidence": "<how heel height/shape were measured>", "model": "<or ''>", "gender": "women|men|unisex|unclear", "price_sources": ["<urls>"]}
}

VINTED CATEGORIES (English UI of vinted.lu, verified for women):
Women > Shoes > {Ballerinas | Boat shoes, loafers & moccasins | Clogs & mules | Espadrilles | Flip-flops & slides | Heels | Lace-up shoes | Mary Janes & T-bar shoes | Sandals | Slippers | Trainers}
Women > Shoes > Boots > {Ankle boots | Mid-calf boots | Knee-high boots | Over-the-knee boots | Snow boots | Wellington boots | Work boots}
Women > Shoes > Sports shoes > … (sub-levels not verified)
Men > Shoes > … (not verified; use the closest analogous English name, e.g. 'Men > Shoes > Trainers', 'Men > Shoes > Boots')
Chelsea boots → Women > Shoes > Boots > Ankle boots.

QUESTIONS — the seller never edits the description by hand. Every uncertain fact is written into the text with a marker AND gets a question whose options rewrite the text:
- Marker styles (description): '${D.confirm}' right after an uncertain claim (e.g. '${D.by} Vagabond ${D.confirm}'), '[?]' for an unknown value (e.g. '${D.sizeLine}[?]', '${D.boxLine}[?]'). The title only uses '[?]' for an unknown value (e.g. '${T.titleSize} [?]').
- Replace pairs: the old and new text of a pair that changes the description are ${dl}${sameReplaceLang ? ', and so are pairs that change the title' : `; pairs that change the title are ${tl}`}. Never add pairs for any other language.
- Question object: {"id": "<short id>", "field": "<field it resolves, optional: brand|size|material|category|condition>", "question": "<question in ${ul}>", "explanation": "<${ul}, why unsure, short>",
   "options": [{"label": "<button text in ${ul}>", "replace": [["<exact old text>", "<new text>"], ["<old>", "<new>", true]], "fields": {"<field>": "<value>"}},
               {"label": "${U.sizeLabel}", "input": true, "placeholder": "${U.sizePlaceholder}", "button": "${U.apply}", "replace": [["${D.sizeLine}[?]", "${D.sizeLine}{value}"], ["${T.titleSize} [?]", "${T.titleSize} {value}"]], "fields": {"size": "{value}"}}]}
  * "replace" pairs are applied to BOTH title and description; "{value}" = the seller's typed input; a third element true = optional (e.g. hashtags that may not exist).
  * The FIRST pair of every option must literally occur in title or description. Pairs that delete text must take the newline or the leading space/separator with them so no extra blank line (never two in a row, none at start/end), double space or ' ,' remains.
  * "fields" use the listing keys and values of the format above (e.g. {"brand": "No brand"}, {"condition": "New without tags"}, {"material": "Faux leather"}).
  * Standard questions (use these button labels; the quoted texts are patterns in the right language — adapt them to the shoe):
    - unknown size: id "size", field size = 'unknown', the input option above (description '${D.sizeLine}[?]', title '${T.titleSize} [?]').
    - likely-but-unconfirmed brand X: description '${D.by} X ${D.confirm}'; options "${U.yesBrand}" (["X ${D.confirm}", "X"]) / "${U.otherBrand}" (input, placeholder "${U.brandPlaceholder}", button "${U.apply}"; also rewrites the brand in the title and removes the brand hashtag with an optional pair) / "${U.noBrand}" (removes ' ${D.by} X ${D.confirm}' or similar, rewrites the title start to e.g. "${T.noBrandTitle}", fields brand 'No brand').
    - unknown brand: description line '${D.brandLine}[?]' with options "${U.brandLabel}" (input, placeholder "${U.brandPlaceholder}", button "${U.apply}") / "${U.noBrand}" (deletes the line: ["\\n${D.brandLine}[?]", ""], fields brand 'No brand').
    - uncertain material: '${D.probably} [?]' with options "${U.matYes}" (→ '${D.real}', material 'Leather') / "${U.matNo}" (→ '${D.faux}', material 'Faux leather') / "${U.matUnsure}" (keeps '${D.probably}' without marker, material '').
    - unclear whether worn: put the claim and what the photos show into one span, e.g. '${D.wear.text}', and let EVERY option replace that whole span, so the answer never contradicts the rest of the text: "${U.wearYes}" → '${D.wear.yes}' (condition 'New without tags') / "${U.wearTried}" → '${D.wear.tried}' (condition 'New without tags') / "${U.wearBrief}" → '${D.wear.brief}' (condition 'Very good'). If a separate '${D.noWear}' sentence follows the claim, put it into the span too: an answer that says worn must never leave it standing. Also rewrite a '${D.newWord}' in front of the claim when an option lowers the condition.
    - optional facts (box, inside zip, outsole not photographed: '${D.outsoleLine}[?]'): options that fill in or delete the fact.
    - gender unclear for unisex trainers: question id "category" with options setting fields category.
  * After answering every question with its FIRST option, no '[?' may remain anywhere. No '[?' without a question.
  * Do not ask about things that are clearly visible.

RULES: Never invent facts (no 'worn twice', 'smoke-free home', 'original box' unless visible, in any language). Brand only from readable text/logo. Size only from a number you actually read. Heel height = an estimate, always ${D.estimate} in the description (the English heel_height field: 'approx. … (estimated)'). All seller-facing texts must be short and plain.
DESCRIPTION TONE (the seller's wish): not critical, not ultra detailed. Mention a flaw in the description ONLY if something is really damaged (hole, tear, broken or loose heel/strap, sole coming off, material rubbed through, missing part, stain that does not come off) — one short clause, e.g. '… (see photos)'. Never mention normal wear or cosmetic trifles (light scuffs, scratches, creases, dust, lint, insole marks, tiny specks, light outsole wear, finishing details, labels/stickers). Record all observed flaws in analysis.flaws and grade "condition" honestly from them — only the description text stays short and positive. No 'Shape:' line, no internal details (maker's marks, label codes, price stickers) unless a buyer needs them.`
}

function analysisPrompt(p, s) {
  const ul = LANG_NAME[s.ui_language]
  return `You create ONE finished Vinted listing for a private seller in Luxembourg (vinted.lu; which text is written in which language is fixed under LANGUAGES below). Today: see system date. Photos of ONE pair of shoes: ${DATA}\\items\\${p.folder}\\ — files: ${p.photos.join(', ')}.

STEPS
1. Look at every photo. Photos may be HEIC/JPG with EXIF rotation: open them with Python (${PY}) via "import sys; sys.path.insert(0, r'${ROOT}'); from vinted_hub.core import open_image; im = open_image(path)" (handles HEIC + rotation), save downscaled JPG copies or zoomed crops to ${OUT}\\_crops\\${p.folder}\\ and Read those. Zoom into insole, tongue, heel, outsole and shaft labels to read brand, size, material, model. Use a pixel grid on a side view to estimate heel/platform height relative to shoe length (outsole ≈ size × 0.667 cm + 1 cm; if size unknown assume EU 39 → ~27 cm and say so).
2. Assess condition honestly (outsole wear, creases, scuffs, dirt) → condition.
3. Price research: load WebSearch/WebFetch via ToolSearch ("select:WebSearch,WebFetch"). Retail price + what similar used items sell for on Vinted/eBay/Kleinanzeigen (FR/BE/LU/DE). Be realistic for Vinted (used shoes sell well below retail; Vinted's own recommendation for a branded espadrille in very good condition was only 7/11/14 €). suggested_price = realistic asking price, suggested_min_price ≈ 75-80 % of it.
4. Write the listing JSON to ${OUT}\\${p.folder}.json (create the folder). Then run: ${CHECK} ${OUT}\\${p.folder}.json — fix and re-run until it prints OK.

${languageRules(s)}
${format(s)}

Return a short summary in ${ul} (brand, size, condition, price suggestion, number of questions, and the final line of the checker output, quoted as is).`
}

function reviewPrompt(p, summary, s) {
  const tl = LANG_NAME[s.title_language], dl = LANG_NAME[s.description_language], ul = LANG_NAME[s.ui_language]
  return `You are an adversarial reviewer of a generated Vinted listing. File: ${OUT}\\${p.folder}.json. Photos: ${DATA}\\items\\${p.folder}\\ (${p.photos.join(', ')}). Open photos via Python: "import sys; sys.path.insert(0, r'${ROOT}'); from vinted_hub.core import open_image; open_image(path)", save crops to ${OUT}\\_crops\\${p.folder}\\ and Read them.

Previous agent's summary: ${summary}

Try to REFUTE each factual claim with your own crops: brand (readable?), size (actually printed?), model, material, condition grade vs. visible wear, every flaw/positive claim in the description, heel height plausibility, category choice. Anything not supported must become uncertain (marker + question) or be removed; anything clearly visible that is asked as a question should be stated instead. Flaws you find go into analysis.flaws (and may lower "condition"), but into the description ONLY if something is really damaged (see DESCRIPTION TONE) — remove normal-wear details from the description. Keep the description short and in the block layout with single blank lines.
Also check the languages (LANGUAGES below): the title is natural, searchable ${tl}; the description is natural ${dl} and nothing else (no line, marker, hashtag or replace text in another language, no separator line); every replace pair is in the language of the text it changes; question, explanation, labels, placeholder, button, hints, price_reasoning and analysis texts are clear ${ul}; data values and "fields" are English ('No brand', 'unknown', condition, color, material, category); "title_language" is "${s.title_language}" and "description_language" is "${s.description_language}". Apply every option in your head: none may leave a contradiction (e.g. '${TEXT[s.description_language].wornBriefly}' followed by '${TEXT[s.description_language].noWear}'). Finally check the price suggestion is realistic for Vinted.
Edit the file directly if needed, keeping the format below, then run ${CHECK} ${OUT}\\${p.folder}.json until it prints OK.

${languageRules(s)}
${format(s)}

Return a short report in ${ul}: what you changed (or "${UI[s.ui_language].noChanges}") and the final line of the checker output, quoted as is.`
}

const { settings, items } = readArgs(args)
const results = await pipeline(
  items,
  p => agent(analysisPrompt(p, settings), { label: `analysis:${p.folder}`, phase: 'Analyse' }),
  (summary, p) => agent(reviewPrompt(p, summary || '(no summary)', settings), { label: `review:${p.folder}`, phase: 'Gegenprüfung' })
    .then(report => ({ folder: p.folder, settings, analysis: summary, review: report })),
)
return results.filter(Boolean)
