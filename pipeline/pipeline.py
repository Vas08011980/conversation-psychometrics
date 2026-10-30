"""Conversation psychometrics pipeline: parse -> scrub -> score -> aggregate.

Turns donated AI-chat exports into daily language indicators parallel to EMA items.
Only the participant's own messages are used (never the AI's). Raw text stays local;
the output holds daily scores only.

Encoders (same interface):
  lsa                     offline TF-IDF + SVD (default; used for the simulated demo)
  st:<model-name>         sentence-transformers, e.g. st:all-mpnet-base-v2
  hf:<model-name>         mean-pooled transformer, e.g. hf:mental/mental-bert-base-uncased (gated)
Usage: python pipeline/pipeline.py --exports demo/data/exports --anchors anchors.yaml --out demo/out
"""
import argparse, glob, json, os, re
from datetime import datetime, timedelta
import numpy as np, pandas as pd, yaml

DAY_START_HOUR = 4  # messages before 04:00 belong to the previous day
PII = [(re.compile(r"\S+@\S+"), "[EMAIL]"), (re.compile(r"\b0\d[\d ]{6,}\b"), "[PHONE]"),
       (re.compile(r"https?://\S+"), "[URL]"), (re.compile(r"\b(?:I am|I'm|this is) [A-Z][a-z]+(?: [A-Z][a-z]+)?"), "[NAME]")]


def parse(path):
    """User messages with timestamps from a ChatGPT-style export."""
    rows = []
    for conv in json.load(open(path)):
        for node in conv.get("mapping", {}).values():
            m = node.get("message") or {}
            if (m.get("author") or {}).get("role") != "user":
                continue
            text = " ".join(p for p in (m.get("content") or {}).get("parts", []) if isinstance(p, str))
            if text.strip():
                rows.append({"ts": m["create_time"], "text": text})
    return rows


def scrub(text):
    for rx, tag in PII:
        text = rx.sub(tag, text)
    return text


def mask(text, words):
    return re.sub(r"\b(" + "|".join(map(re.escape, words)) + r")\w*\b", "[MASK]", text, flags=re.I)


class Encoder:
    def __init__(self, spec, corpus):
        self.spec = spec
        if spec == "lsa":
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.decomposition import TruncatedSVD
            self.vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True).fit(corpus)
            X = self.vec.transform(corpus)
            self.svd = TruncatedSVD(n_components=min(100, X.shape[1] - 1), random_state=0).fit(X)
        elif spec.startswith("st:"):
            from sentence_transformers import SentenceTransformer
            self.m = SentenceTransformer(spec[3:])
        elif spec.startswith("hf:"):
            from transformers import AutoTokenizer, AutoModel
            self.tok = AutoTokenizer.from_pretrained(spec[3:]); self.m = AutoModel.from_pretrained(spec[3:])

    def __call__(self, texts):
        if self.spec == "lsa":
            E = self.svd.transform(self.vec.transform(texts))
        elif self.spec.startswith("st:"):
            E = self.m.encode(texts)
        else:
            import torch
            with torch.no_grad():
                b = self.tok(texts, padding=True, truncation=True, return_tensors="pt")
                h = self.m(**b).last_hidden_state; a = b["attention_mask"].unsqueeze(-1)
                E = ((h * a).sum(1) / a.sum(1)).numpy()
        E = np.asarray(E, float)
        return E / np.clip(np.linalg.norm(E, axis=1, keepdims=True), 1e-9, None)


def run(exports, anchors, out, encoder="lsa"):
    A = yaml.safe_load(open(anchors)); cons = [c for c in A if c != "neutral"]
    msgs = []
    for f in sorted(glob.glob(f"{exports}/*.json")):
        pid = os.path.splitext(os.path.basename(f))[0]
        for r in parse(f):
            t = datetime.fromtimestamp(r["ts"]) - timedelta(hours=DAY_START_HOUR)
            msgs.append({"id": pid, "date": t.date(), "text": scrub(r["text"])})
    df = pd.DataFrame(msgs)
    first = df.groupby("id")["date"].transform("min")
    df["day"] = (pd.to_datetime(df["date"]) - pd.to_datetime(first)).dt.days + 1
    anchor_txt = {c: [A[c]["item"]] + A[c]["paraphrases"] for c in A}
    all_words = sorted({w for c in cons for w in A[c].get("lexicon", [])})
    masked = df["text"].apply(lambda s: mask(s, all_words))
    corpus = list(df["text"]) + list(masked) + [s for v in anchor_txt.values() for s in v]
    enc = Encoder(encoder, corpus)
    Em, Emask = enc(list(df["text"])), enc(list(masked))
    neutral = enc(anchor_txt["neutral"])
    for c in cons:
        Ea = enc(anchor_txt[c])
        base = lambda E: (E @ neutral.T).max(1)
        df[f"ind_{c}"] = (Em @ Ea.T).max(1) - base(Em)               # closeness to construct vs neutral tasks
        df[f"ind_{c}_masked"] = (Emask @ Ea.T).max(1) - base(Emask)  # same, topic words masked
    df["n_chars"] = df["text"].str.len()
    agg = {**{k: "mean" for k in df.columns if k.startswith("ind_")}, "n_chars": "sum", "text": "count"}
    day = df.groupby(["id", "day"]).agg(agg).rename(columns={"text": "n_msgs"}).reset_index()
    os.makedirs(out, exist_ok=True)
    day.to_csv(f"{out}/day_scores.csv", index=False)
    # blind-rating sample: 80 random conversation-days, text kept local for raters only
    samp = day.sample(min(80, len(day)), random_state=1)[["id", "day"]]
    keep = df.merge(samp, on=["id", "day"]).groupby(["id", "day"])["text"].apply(" || ".join).reset_index()
    keep.to_csv(f"{out}/rating_sample_LOCAL_ONLY.csv", index=False)
    print(f"{len(df)} user messages -> {len(day)} person-days; encoder={encoder}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--exports", required=True); a.add_argument("--anchors", default="anchors.yaml")
    a.add_argument("--out", default="demo/out"); a.add_argument("--encoder", default="lsa")
    run(**vars(a.parse_args()))
