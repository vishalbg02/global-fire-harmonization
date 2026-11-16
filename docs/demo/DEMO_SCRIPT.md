# Demo script (T-060)

**For:** the live presentation and the recorded video (T-061). Every number below is a stored value of the final products (verified in T-079, T-078, T-081 and T-093). Do not say any number that is not on this page or on screen.

**Before you start:**
- API on port 8000 and app on 5173 (see `README.md`), or the offline copy (`api/README.md`).
- Browser full screen, at 1280x720 or larger (the whole answer fits at 1280x720).
- Open `http://localhost:5173/`. It opens on the globe in dark space, with **Start here** on the right.
- To show the first-visit tour, use a private window, or click **Help → Take the tour**. A browser that dismissed help before doesn't show it again.

**Where things are (layout since T-093):**
- **The Earth**, on the left. One **control dock** sits top-left:
  - area search
  - Flat/Globe
  - Satellite view
  - Select area
  - **Layers** (Raw/Harmonized, Verdict/Activity)

  The legend strip is bottom-left, with **Show all verdicts**. Zoomed out, only above- and below-normal cells are drawn strongly. The pause button for the slow globe rotation sits by the zoom buttons.
- **The answer panel**, on the right. The story chips are at the top, then in order:
  - the verdict
  - the big **% of normal**
  - the probability
  - the **interval bar** (the estimate and its 90% interval against the hatched normal range)
  - the sparkline
  - **Why** chips that open the reasons
  - the source line
  - actions: Download CSV, Copy link, Compare with…, Details

  Every **?** opens a two-line explanation with **Learn more**.
- **The timeline**, under the map: a 2002–2026 strip with a faint line of monthly activity. The **S-NPP VIIRS** and **NOAA-20 VIIRS** start dates are marked, provisional months are shaded, and **Play** and **Choose a month** are there.
- **The Details tabs**, below the first screen: Calendar, Satellites, Evidence, All anomalies, Analytics.
- **Help** in the header: the tour, how to read the map, and the keyboard shortcuts (press **?**).

## The 30-second version

> "Satellite fire records jump every time a new satellite joins. That's not fire, it's the camera changing. We put NASA's MODIS and VIIRS satellites on one scale, so for any place and month since 2002 you can ask: was fire activity really unusual? We answer with a verdict, a probability and the evidence, and we publish our own tests, including the 18 that failed."

## The 3-minute version

| Time | Do | Say |
|---|---|---|
| 0:00 | The app opens on the **globe**. Drag it to turn the Earth. Only the orange (above) and blue (below normal) cells stand out | "This is NASA FIRMS fire data from 2002 to today, harmonized across five satellites, on NASA's Blue Marble. Zoomed out, we only draw what is unusual, so the signal isn't lost in noise." |
| 0:20 | In **Start here**, click **Was Indonesia's fire activity in September 2015 unusual?** The map flies there | "September 2015, Indonesia. Above normal: 265% of normal, more than 99% likely. This bar shows it: the estimate and its 90% interval, 17,320 to 20,817 fire-active cell-days, sit far to the right of the hatched normal range." |
| 0:50 | Point at the **timeline**: the dashed **S-NPP** and **NOAA-20** marks. Then dock → **Layers → Raw**, then back to **Harmonized** (or Details → **Analytics**, first chart) | "Here's the problem we solve. The raw count jumps in 2012 when S-NPP joins, and again in 2018 with NOAA-20. That jump is a satellite, not fire. The harmonized line stays on one scale." |
| 1:20 | Story chip **Canada, Aug 2023**. Then drag the timeline, or press **Play** | "Canada, August 2023: ten times its normal August, 1024% of normal, rank 1 of 22 countries that month. Any month since 2002 is one drag away." |
| 1:50 | Story chip **Australia, Dec 2019**, then click a **Why** chip | "The country is above normal at 328%. But many single cells say 'cannot determine': where a place almost never burns, there's no normal to compare with, so we don't guess. Every answer says why." |
| 2:15 | Story chip **Brazil, Aug 2019** (optional: dock → **Satellite view** for the real Aqua image of that day) | "Brazil, August 2019, famous in the news: satellite-detected activity was within its normal range, 114%. We report the data, not the headline." |
| 2:30 | Header **Methods and validation** | "We wrote our tests before seeing any result: 38 results, 18 pass, 18 fail, shown just as clearly. The biggest failure: in extreme months the converted VIIRS reads 20 to 40% low, and we say so." |
| 2:50 | Back to the map | "Satellites keep changing. With this, the fire record doesn't have to, and it tells you when it can't be sure." |

## If a judge asks

- **"Is it easy for a first-time user?"** Click **Help → Take the tour** (five steps on the real screen), or tap any **?** next to a term.
- **"Does it work on a phone?"** On a phone the answer is a bottom sheet you drag up over the map, and the dock becomes icon buttons.
- **"Keyboard?"** Press **?**: ← → change the month, PageUp/PageDown the year, Space plays, G switches the globe, S Satellite view, / searches.

## If something goes wrong

- **No network (imagery):** the map falls back to the plain background. Say "NASA imagery needs the internet; the data doesn't" and carry on.
- **The API is down:** open the offline copy (see `api/README.md`; a 24-month copy was tested in T-081).
- **A judge asks for a number not on screen:** "That is in the CSV and the methods page; I won't guess."

## Words to use and to avoid

- **Say:** "satellite-detected fire activity", "fire-active cell-days", "verdict", "cannot determine is a result", "validated in sampled regions".
- **Never say:** "number of fires", "burned area", "the validation passed", "accurate everywhere".
