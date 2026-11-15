# Demo script (T-060)

**For:** the live presentation and the recorded video (T-061). Every number below is a stored value of the final products (verified in T-079, T-078 and T-081). Do not say any number that is not on this page or on screen.

**Before you start:**
- API on port 8000 and app on 5173 (see `README.md`), or the offline copy (`api/README.md`).
- Browser full screen, at 1280x720 or larger.
- Open `http://localhost:5173/`, close the "How to read this" panel once, and reload.

## The 30-second version

> "Satellite fire records jump every time a new satellite joins. That's not fire, it's the camera changing. We put NASA's MODIS and VIIRS satellites on one scale, so for any place and month since 2002 you can ask: was fire activity really unusual? We answer with a verdict, a probability and the evidence, and we publish our own tests, including the 18 that failed."

## The 3-minute version

| Time | Do | Say |
|---|---|---|
| 0:00 | Show the app at world view. Switch **Map view → Globe** and zoom out with **−** | "This is NASA FIRMS fire data from 2002 to today, harmonized across five satellites, on NASA's Blue Marble." |
| 0:20 | Click the story chip **Indonesia, Sep 2015** | "September 2015, Indonesia. Above normal: 265% of normal, more than 99% likely. The 90% interval is 17,320 to 20,817 fire-active cell-days. Below it: the satellites used and the source." |
| 0:50 | Open the **Analytics** tab, first chart | "Here's the problem we solve. The raw count jumps in 2012 when S-NPP joins, and again in 2018 with NOAA-20. That jump is a satellite, not fire. The harmonized line stays on one scale." |
| 1:20 | Story chip **Canada, Aug 2023** | "Canada, August 2023: ten times its normal August, 1024% of normal, rank 1 of 22 countries that month." Then use **Choose a month** to jump to another month in two clicks, or press **Play**. |
| 1:50 | Story chip **Australia, Dec 2019** | "The country is above normal at 328%. But many single cells say 'cannot determine': where a place almost never burns, there's no normal to compare with, so we don't guess." |
| 2:15 | Story chip **Brazil, Aug 2019** | "Brazil, August 2019, famous in the news: satellite-detected activity was within its normal range, 114%. We report the data, not the headline." |
| 2:30 | Header **Methods and validation** | "We wrote our tests before seeing any result: 38 results, 18 pass, 18 fail, shown just as clearly. The biggest failure: in extreme months the converted VIIRS reads 20 to 40% low, and we say so." |
| 2:50 | Back to the map | "Satellites keep changing. With this, the fire record doesn't have to, and it tells you when it can't be sure." |

## If something goes wrong

- **No network (imagery):** the map falls back to the plain background. Say "NASA imagery needs the internet; the data doesn't" and carry on.
- **The API is down:** open the offline copy (see `api/README.md`; a 24-month copy was tested in T-081).
- **A judge asks for a number not on screen:** "That is in the CSV and the methods page; I won't guess."

## Words to use and to avoid

- **Say:** "satellite-detected fire activity", "fire-active cell-days", "verdict", "cannot determine is a result", "validated in sampled regions".
- **Never say:** "number of fires", "burned area", "the validation passed", "accurate everywhere".
