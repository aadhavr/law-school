# MANUAL_DOWNLOADS.md

These sites blocked automated download, so I did not work around them. Please save each file into the folder shown. Keep the original file names. Then tell me, and I will hash the files and add them to `DATA_SOURCES.md`.

## 1. ABA legal education statistics → `data/raw/04_aba/`

All three URLs returned **HTTP 403** to the download script on 2026-10-24.

**a. Statistics page:** https://www.americanbar.org/groups/legal_education/resources/statistics/
1. Open the link in your browser.
2. Save the page: File → Save Page As… → Format "Web Page, HTML Only" → save to `data/raw/04_aba/`.
3. On the page, look for the historical enrollment data, likely titled something like "Enrollment and Degrees Awarded" (1963–2012 or later). Download its Excel version (or the PDF if there is no Excel) into `data/raw/04_aba/`. This is the file most likely to fill need (c), JD counts by year.
4. Also look for the aggregate Standard 509 data files ("JD Enrollment", "Degrees Awarded", one per year after 2011). Download the Excel files for the years you want.

**b. News page (2022):** https://www.americanbar.org/news/abanews/aba-news-archives/2022/12/aba-legal-ed-data-update/
- Open it, then File → Save Page As… → "Web Page, HTML Only" → `data/raw/04_aba/`.

**c. News page (2021):** https://www.americanbar.org/news/abanews/aba-news-archives/2021/12/aba-website-updates-data-on-law-school-admissions-tuition/
- Same steps as (b).

## 2. IGM Forum → `data/raw/05_igm/`

`https://www.igmchicago.org` returned **HTTP 403** to the script. `https://igmchicago.org` failed the TLS handshake (this site, and no other in the batch, failed this way). Because I could not open the site, **I cannot say whether it offers a download of panel results.**
1. Open https://www.igmchicago.org in your browser. It may redirect. The IGM Forum surveys may now be hosted under a new name (the Clark Center); I have not confirmed this.
2. Look for a download, export, or "data" link for the US Economic Experts Panel results (statement text plus each expert's vote and confidence).
3. If one exists, save it to `data/raw/05_igm/`. If none exists, tell me, and I will record "no download offered" in `DATA_SOURCES.md`. Do not copy survey pages by hand without checking the site's terms first.

## 3. Optional: Washington and Lee 509 report → `data/raw/13_aba_509/`

The W&L disclosures page (already saved) links its 2025 Standard 509 Report on Box (https://wlu.box.com/s/7rtpifx6kujjz38cmdzlj6rsk6f6wbig). Box share pages are viewers, not direct files. I did not try them, because you asked only for the pages. If you want the PDF, open the link and click Download.

## 4. GovTrack bulk bill data (Test D, predictors b and c) → `data/raw/14_govtrack/`
On 2026-10-27, `https://www.govtrack.us/about-our-data`, `/data/` and `/data/congress/` all returned **HTTP 403** to the script. GovTrack's robots.txt allows `*` but disallows Anthropic's crawlers (ClaudeBot, anthropic-ai, Claude-Web). It also sets `Content-Signal: search=yes, ai-train=no, use=reference`. I did not try any other route to GovTrack. **Do not download yet.** First decide the source (govinfo BILLSTATUS vs GovTrack, see my report). If you choose GovTrack:
1. Open https://www.govtrack.us/data/congress/ in your browser and check the terms on https://www.govtrack.us/about-our-data.
2. GovTrack stores one folder per bill (`congress/<n>/bills/hr/hr<k>/data.json`), with no single archive per Congress. Get only `bills/hr` and `bills/hjres` for the Congresses you choose, and save them under `data/raw/14_govtrack/congress/`.

## 5. Fowler cosponsorship data (possible source for Congresses 93–107) → `data/raw/16_fowler/`
`https://jhfowler.ucsd.edu/cosponsorship.htm`: the robots.txt request failed at the network level (URLError) on 2026-10-27, so the script treated the site as disallowed. Not needed unless you choose to cover Congresses before 108. If so, open the page in your browser and tell me what files it offers.
