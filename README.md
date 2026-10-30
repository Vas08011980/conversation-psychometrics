# conversation-psychometrics

**Can what young people say to AI chatbots be measured as soundly as their survey answers?**
Prototype pipeline (v0.2.0) that turns donated AI-chat text into daily wellbeing indicators and puts each indicator through three preregistered validity tests. Demonstrated here on fully simulated data.

**Interactive demo website:** [https://vas08011980.github.io/conversation-psychometrics/](https://vas08011980.github.io/conversation-psychometrics/)

Vasileios Stavropoulos (RMIT University) · Spyridon Kavvadias

## How it works

1. **Parse** a donated ChatGPT-style export; keep only the participant's own messages (never the AI's); assign each to a study day (messages before 04:00 count to the previous day).
2. **Protect**: emails, phone numbers, links and self-introduced names are removed locally. Only daily scores leave the machine.
3. **Score**: each construct has anchors, the daily survey item (e.g. "I felt lonely") plus paraphrases (`anchors.yaml`). Each message is scored for closeness in meaning to the construct, relative to neutral task requests; scores are averaged per person-day.
4. **Test** each indicator (`tests/tests.R`):
   - **(i) Convergence**: within-person correlation with its own daily survey item ≥ .20, and higher than with every other construct (it must capture loneliness, not general negativity).
   - **(ii) Robustness**: (i) must hold controlling for message length and with topic words masked (writing *about* loneliness is not feeling lonely).
   - **(iii) Human agreement**: two blind raters agree (ICC ≥ .60) and the indicator tracks their ratings (r ≥ .30).
   Indicators that fail are reported, not dropped silently: a negative result is informative.

The encoder is pluggable: `lsa` (offline TF-IDF + SVD, used in the demo), `st:<model>` (sentence-transformers) or `hf:<model>` (mean-pooled transformer, e.g. `hf:mental/mental-bert-base-uncased`). Comparing encoders on the same tests is itself a robustness check.

## Demo on simulated data

`simulate/simulate.py` creates 60 young adults × 14 days: daily states (loneliness, stress, low mood, low self-esteem; correlated .30), noisy daily survey answers, and chat exports in which each person voices their state with a personal probability. Built-in traps: some people write *about* loneliness as a topic; self-esteem is rarely voiced in chats (it should fail); personal details appear in text (they should be removed).

```bash
pip install -r requirements.txt
./run_demo.sh   # simulate -> pipeline -> tests -> website (docs/index.html)
```

Results (`demo/out/test_results.csv`, seed 2026, offline encoder):

| Indicator | Within-person r [95% CI] | Highest r with other constructs | Length-controlled r | Topic-masked r | Rater ICC | r with raters | Passes all three |
|---|---|---|---|---|---|---|---|
| Loneliness | .22 [.15, .28] | .11 | .22 | .22 | .74 | .35 | Yes |
| Stress | .22 [.16, .29] | .09 | .21 | .21 | .79 | .44 | Yes |
| Low mood | .22 [.16, .28] | .09 | .22 | .20 | .78 | .52 | Yes |
| Low self-esteem | .14 [.07, .21] | .10 | .14 | .14 | .85 | .30 | **No** (rarely voiced) |

The pipeline recovers what was built into the data and rejects the indicator it should reject.

**Limits.** These are simulated data generated from templates, so the results show that the method works end to end, not that real AI conversations carry valid wellbeing signal; that is the empirical question the method is built to test. Raters in the demo are simulated from what each day's text voices; in a real study, two trained raters code `rating_sample_LOCAL_ONLY.csv` blind to survey answers and indicators.

## Interactive website

[`docs/index.html`](https://vas08011980.github.io/conversation-psychometrics/) presents the same simulated demo as a website, built from the files above by `site/build_site.py` (the last step of `run_demo.sh`). It contains no data beyond what the demo generates, and its numbers come straight from `demo/out/test_results.csv` and the pipeline's daily scores (the build stops if the message-level scores do not reproduce `day_scores.csv`). Visitors can:

- **Explore the data**: pick any of the 60 simulated participants and a construct, compare the daily survey answer with the language indicator across 14 days, and read each day's messages as typed, after personal details are removed, and with topic words masked, with each message's scores.
- **Score a message**: the offline demo encoder runs in the browser (nothing typed leaves the page). It only knows the vocabulary of the simulated chats.
- **See the validity tests**: pass/fail on the three tests for each indicator, and the within-person correlation of every indicator with every daily survey item (the discriminant check in test i).
- **See the built-in traps**: topic writers, the rarely voiced self-esteem indicator, and personal details in text.

## Files

| Path | Content |
|---|---|
| `anchors.yaml` | Construct anchors, paraphrases and masking lexicons (editable) |
| `simulate/simulate.py` | Simulated participants, daily surveys and chat exports |
| `pipeline/pipeline.py` | Parse, scrub, score, aggregate |
| `tests/tests.R` | The three validity tests |
| `demo/out/test_results.csv` | Demo results |
| `site/build_site.py` | Builds the interactive website from the demo outputs |
| `site/page_*.html`, `site/page_script.js` | Website layout and interactive code |
| `docs/index.html` | The interactive website (served by GitHub Pages) |
| `run_demo.sh` | Runs everything |

MIT licence. Cite via `CITATION.cff`.
