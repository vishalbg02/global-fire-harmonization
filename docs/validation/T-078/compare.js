// T-078: run in the real app (Vite dev server, real API on the real products) on a URL like /?area=COUNTRY:IDN&month=2015-09.
// It compares what the page shows with app/public/_t078/expected.json (made by expected.py from the products), for the summary
// card, the sparkline table, the story caption and the Analytics tab. It returns {checks, mismatches}.
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim()
  const exp = await (await fetch('/_t078/expected.json')).json()
  const p = new URLSearchParams(location.search)
  const key = p.get('area') === null || p.get('area') === 'GLOBAL' ? 'GLOBAL:GLOBAL' : p.get('area') // the world is the default area: no `area` in the link
  const e = exp.find((c) => c.id === key && c.month === p.get('month'))
  const out = { url: location.search, checks: 0, mismatches: [] }
  const check = (name, expected, shown) => {
    out.checks += 1
    if (JSON.stringify(expected) !== JSON.stringify(shown)) out.mismatches.push({ name, expected, shown })
  }
  if (!e) return JSON.stringify({ error: 'no expectation for ' + location.search })
  await sleep(3500)
  const sm = document.querySelector('.summary')
  check('summary title', e.summary.title, norm(sm.querySelector('h2')?.textContent))
  check('verdict label', true, norm(sm.querySelector('.summary-verdict')?.textContent).includes(e.summary.verdict))
  check('probability sentence', e.summary.prob, sm.querySelector('.prob') ? norm(sm.querySelector('.prob').textContent) : null)
  check('% of normal', e.summary.big, sm.querySelector('.big') ? norm(sm.querySelector('.big').textContent) : null)
  const dd = [...sm.querySelectorAll('dd')].map((d) => norm(d.textContent))
  check('estimate', true, (dd[0] || '').startsWith(e.summary.estimate + ' '))
  check('90% interval', e.summary.interval, dd[1])
  check('satellites', e.summary.satellites, dd[2])
  const reasons = sm.querySelectorAll('.reason li').length
  check('reason lines', e.summary.reasons.length, reasons === 0 ? 0 : reasons)
  if (e.summary.reasons.length === 0) check('no-caveat text', true, norm(sm.querySelector('.reason')?.textContent).includes('No caveat flags are recorded'))
  check('data level text', true, norm(sm.querySelector('.source-line')?.textContent).includes(e.summary.level === 'SP' ? 'standard (SP)' : 'near-real-time (NRT)'))
  check('provisional notice', e.summary.level !== 'SP', !!sm.querySelector('.evidence-provisional'))
  const rows = [...sm.querySelectorAll('.spark table tbody tr')].map((r) => [...r.cells].map((c) => norm(c.textContent)))
  check('sparkline rows', e.spark, rows)
  // the story caption (if this area and month is a featured story) equals featured.ts, and featured.ts facts equal the stored values
  const feat = (await import('/src/content/featured.ts')).FEATURED_STORIES
  const story = feat.find((s) => (s.entityType === 'GLOBAL' ? 'GLOBAL:GLOBAL' : s.entityType + ':' + s.entityId) === e.id && `${s.year}-${String(s.month).padStart(2, '0')}` === e.month)
  const cap = document.querySelector('.story-caption')
  check('story caption present for a featured case', true, !!cap)
  if (story && cap) {
    check('story headline', story.headline, norm(cap.querySelector('h3')?.textContent))
    check('story caption text', norm(story.caption), norm(cap.querySelector('.story-body p')?.textContent))
    check('story label', '[VERIFIED]', norm(cap.querySelector('.story-label')?.textContent))
    check('story facts pct', e.summary.raw.pct, story.facts.pctOfNormal)
    check('story facts estimate', e.summary.raw.est, story.facts.estimate)
    check('story facts interval', [e.summary.raw.lo, e.summary.raw.hi], [story.facts.ci90Low, story.facts.ci90High])
    check('story caption shows the rounded % of normal', true, norm(story.caption).startsWith(`${Math.round(e.summary.raw.pct)}%`))
  }
  // Analytics tab
  const tab = [...document.querySelectorAll('[role=tab]')].find((t) => norm(t.textContent) === 'Analytics')
  tab?.click()
  await sleep(4500)
  const an = document.querySelector('.analytics')
  check('analytics mounted', true, !!an)
  if (an) {
    const tables = [...an.querySelectorAll('details table')]
    const cellsOf = (t) => [...t.querySelectorAll('tbody tr')].map((r) => [...r.cells].map((c) => norm(c.textContent)))
    check('annual sums table', e.annual, cellsOf(tables[0]))
    check('season profile table', e.season, cellsOf(tables[1]))
    const rankLines = [...an.querySelectorAll('#an-rank ~ *, .analytics-rank, .analytics-rank + .analytics-note')].map((x) => norm(x.textContent))
    check('rank first line', e.rank[0], norm(an.querySelector('.analytics-rank')?.textContent))
    const rankSection = norm(an.querySelector('.analytics-rank')?.parentElement?.textContent)
    for (const line of e.rank.slice(1)) check('rank line: ' + line.slice(0, 30), true, rankSection.includes(line))
    const cov = an.querySelector('.analytics-coverage')
    if (e.coverage) {
      check('coverage line (world)', e.coverage.line, norm(cov?.textContent))
      const li = [...an.querySelectorAll('#an-coverage ~ ul li, section[aria-labelledby=an-coverage] li')].map((x) => norm(x.textContent))
      check('coverage verdict breakdown count lines', Object.keys(e.coverage.by_verdict).length, li.length)
    } else {
      check('coverage: world-only message for a country', true, norm(an.textContent).includes('shown for the world only'))
      check('coverage: no figure for a country', false, !!cov)
    }
    check('annual note', true, norm(an.textContent).includes('Sum of monthly estimates; intervals not combined'))
  }
  out.synthetic_text_on_page = /SYNTHETIC/i.test(document.body.innerText)
  return JSON.stringify(out)
})()
