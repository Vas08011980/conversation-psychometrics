"""Build the interactive demo website (docs/index.html) from the simulated demo.

Run after ./run_demo.sh:  python3 site/build_site.py
Reuses pipeline/pipeline.py (parse, scrub, mask, offline encoder) to recover
message-level scores, and reads demo/data and demo/out. Simulated data only.
"""
import glob, json, os, sys
from datetime import datetime, timedelta
import numpy as np, pandas as pd, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import pipeline as P  # noqa: E402

DATA, OUT, SITE = f"{ROOT}/demo/data", f"{ROOT}/demo/out", f"{ROOT}/site"
C = ["loneliness", "stress", "mood", "self_esteem"]
TOPIC = ["write an essay on loneliness in modern cities", "what does research say about loneliness and social media",
         "give me statistics on youth loneliness in Australia", "summarise a paper on isolation in older adults"]

# ---- message-level scores, exactly as pipeline.run() computes them ----
A = yaml.safe_load(open(f"{ROOT}/anchors.yaml"))
rows = []
for f in sorted(glob.glob(f"{DATA}/exports/*.json")):
    pid = os.path.splitext(os.path.basename(f))[0]
    for r in P.parse(f):
        t = datetime.fromtimestamp(r["ts"]) - timedelta(hours=P.DAY_START_HOUR)
        rows.append({"id": pid, "date": t.date(), "raw": r["text"], "text": P.scrub(r["text"])})
msg = pd.DataFrame(rows)
first = msg.groupby("id")["date"].transform("min")
msg["day"] = (pd.to_datetime(msg["date"]) - pd.to_datetime(first)).dt.days + 1
anchor_txt = {c: [A[c]["item"]] + A[c]["paraphrases"] for c in A}
lex = sorted({w for c in C for w in A[c].get("lexicon", [])})
msg["masked"] = msg["text"].apply(lambda s: P.mask(s, lex))
corpus = list(msg["text"]) + list(msg["masked"]) + [s for v in anchor_txt.values() for s in v]
enc = P.Encoder("lsa", corpus)
E, neu = enc(list(msg["text"])), enc(anchor_txt["neutral"])
for c in C:
    msg[f"ind_{c}"] = (E @ enc(anchor_txt[c]).T).max(1) - (E @ neu.T).max(1)

# ---- check against the pipeline's own day scores ----
day = pd.read_csv(f"{OUT}/day_scores.csv")
chk = msg.groupby(["id", "day"])[[f"ind_{c}" for c in C]].mean().reset_index().merge(day, on=["id", "day"], suffixes=("", "_p"))
assert all(np.allclose(chk[f"ind_{c}"], chk[f"ind_{c}_p"]) for c in C), "message scores do not match day_scores.csv"

ema = pd.read_csv(f"{DATA}/ema.csv").pivot_table(index=["id", "day"], columns="construct", values="score").reset_index()
truth = pd.read_csv(f"{DATA}/truth.csv")
res = pd.read_csv(f"{OUT}/test_results.csv")

# within-person r of every indicator with every daily survey item (same as tests.R, test i)
m = day.merge(ema, on=["id", "day"])
wc = lambda x: x - x.groupby(m["id"]).transform("mean")
cm = [[round(float(np.corrcoef(wc(m[f"ind_{a}"]), wc(m[b]))[0, 1]), 3) for b in C] for a in C]

texts = sorted(set(msg["raw"]) | set(msg["text"]) | set(msg["masked"]))
ti = {t: i for i, t in enumerate(texts)}
people = {}
for pid, g in msg.groupby("id", sort=True):
    d = day[day.id == pid].merge(ema, on=["id", "day"]).merge(truth, on=["id", "day"]).sort_values("day")
    days = []
    for _, r in d.iterrows():
        mm = g[g.day == r.day]
        days.append({"d": int(r.day), "ema": [int(r[c]) for c in C], "ind": [round(r[f"ind_{c}"], 4) for c in C],
                     "shown": [r[f"shown_{c}"] for c in C],
                     "m": [[ti[x.raw], ti[x.text], ti[x.masked], [round(getattr(x, f"ind_{c}"), 3) for c in C]]
                           for x in mm.itertuples()]})
    people[pid] = {"days": days, "topic": bool(g["raw"].isin(TOPIC).any())}

vocab = enc.vec.vocabulary_
model = {"vocab": sorted(vocab, key=vocab.get), "idf": [round(x, 5) for x in enc.vec.idf_],
         "comp": [[round(v, 5) for v in row] for row in enc.svd.components_.T.tolist()],
         "anchors": {c: [[round(v, 5) for v in r] for r in enc(anchor_txt[c]).tolist()] for c in A},
         "anchor_text": anchor_txt, "lexicon": lex}
data = {"C": C, "texts": texts, "people": people, "results": res.to_dict(orient="records"), "cm": cm,
        "model": model, "n_msgs": int(len(msg)), "n_days": int(len(day)),
        "n_pii": int((msg.raw != msg.text).sum()), "n_topic": int(sum(p["topic"] for p in people.values()))}

js = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
page = (open(f"{SITE}/page_head.html").read() + open(f"{SITE}/page_body.html").read()
        + f'<script type="application/json" id="data">{js}</script>\n<script>\n'
        + open(f"{SITE}/page_script.js").read() + "</script>\n")
html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
        + page.replace("</style>\n", "</style>\n</head>\n<body>\n", 1) + "</body>\n</html>\n")
os.makedirs(f"{ROOT}/docs", exist_ok=True)
open(f"{ROOT}/docs/index.html", "w").write(html)
print(f"docs/index.html written ({len(html)//1024} KB): {len(msg)} messages, {len(day)} person-days")
