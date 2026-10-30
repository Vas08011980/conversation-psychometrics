"""Simulate young adults, daily EMA and donated AI-chat exports (no real data).

Each person has daily latent states (loneliness, stress, low mood, low self-esteem).
EMA answers are noisy reports of those states. Chat messages express a state only
with a person-specific probability ("expressivity"); most messages are ordinary tasks.
Built-in traps: some people write ABOUT loneliness as a topic regardless of how they
feel; self-esteem is rarely expressed in chats (expected to fail); PII appears in text.
Usage: python simulate/simulate.py --n 60 --days 14 --seed 2026 --out demo/data
"""
import argparse, json, os, random
from datetime import datetime, timedelta
import numpy as np

C = ["loneliness", "stress", "mood", "self_esteem"]
EXPRESS = {  # explicit and implicit expressions of each state
    "loneliness": ["honestly I feel so lonely lately", "nobody replied to my messages again",
                   "ate dinner by myself again tonight", "I wish I had someone to talk to right now",
                   "everyone has plans except me", "can you just chat with me for a bit, there's no one else",
                   "my friends haven't messaged in days", "I feel invisible to everyone around me"],
    "stress": ["I have three assignments due tomorrow and I'm panicking", "I can't keep up with work and uni",
               "everything is piling up and I don't know where to start", "my boss keeps adding tasks, I'm so overwhelmed",
               "I didn't sleep because of the deadline", "help me make a plan, I'm completely swamped",
               "my heart is racing thinking about the exam", "too many things to do and no time"],
    "mood": ["I feel really low today", "nothing seems worth doing anymore", "I stayed in bed most of the day",
             "everything feels grey", "I cried for no reason this morning", "I can't enjoy anything lately",
             "today was just heavy", "I don't feel like myself"],
    "self_esteem": ["I'm not good enough for this job", "everyone is smarter than me", "I hate how I look in photos",
                    "I always mess everything up", "why would anyone want to be friends with me",
                    "I feel like such a failure"],
}
TOPIC = ["write an essay on loneliness in modern cities", "what does research say about loneliness and social media",
         "give me statistics on youth loneliness in Australia", "summarise a paper on isolation in older adults"]
NEUTRAL = ["what is the capital of Portugal", "write a python function to sort a list", "give me a recipe for pasta",
           "summarise this article about climate policy", "fix the grammar in my cover letter",
           "explain photosynthesis simply", "suggest a workout for beginners", "translate this into Spanish",
           "how do I reference a website in APA", "plan a weekend trip to Sydney", "what movies are like Inception",
           "help me write an email to my landlord", "how does compound interest work", "debug this javascript error"]
PII = ["my email is jess.taylor{}@gmail.com", "call me on 04{} 555 123", "this is Sam {} from Brunswick"]
ASSIST = ["Sure, here is what I found.", "That sounds hard. Would you like to talk about it?", "Here is a step-by-step plan."]


def main(n=60, days=14, seed=2026, out="demo/data"):
    rng = np.random.default_rng(seed); random.seed(seed)
    os.makedirs(f"{out}/exports", exist_ok=True)
    R = np.full((4, 4), .3) + np.eye(4) * .7          # states correlate .30 (discriminant validity matters)
    L = np.linalg.cholesky(R)
    ema, truth = [], []
    start = datetime(2028, 3, 1)
    for i in range(n):
        pid = f"P{i+1:03d}"
        person = (L @ rng.normal(size=4)) * .6         # stable between-person level
        expr = rng.beta(4, 2)                          # expressivity: share of messages showing state
        topic_writer = rng.random() < .25              # writes ABOUT loneliness as a topic
        convs = []
        for d in range(days):
            state = person + (L @ rng.normal(size=4)) * .8   # daily state
            for c, s in zip(C, state):                       # EMA 1-7, higher = worse
                ema.append({"id": pid, "day": d + 1, "construct": c,
                            "score": int(np.clip(round(4 + 1.2 * s + rng.normal(0, .8)), 1, 7))})
            msgs, shown = [], dict.fromkeys(C, 0)
            for _ in range(rng.poisson(4) + 1):
                if rng.random() < expr:
                    w = np.exp(state * 2) * np.array([1, 1, 1, .15])   # self-esteem rarely voiced
                    c = rng.choice(4, p=w / w.sum())
                    if state[c] > -0.2:
                        txt = random.choice(EXPRESS[C[c]]); shown[C[c]] += 1
                    else:
                        txt = random.choice(NEUTRAL)
                else:
                    txt = random.choice(NEUTRAL)
                if topic_writer and rng.random() < .4:
                    txt = random.choice(TOPIC)
                if rng.random() < .03:
                    txt += ". " + random.choice(PII).format(random.randint(10, 99))
                msgs.append(txt)
            truth.append({"id": pid, "day": d + 1, **{f"true_{c}": round(float(v), 3) for c, v in zip(C, state)},
                          **{f"shown_{c}": round(shown[c] / len(msgs), 3) for c in C}})  # share of messages voicing it
            t = start + timedelta(days=d, hours=int(rng.integers(8, 23)))
            mapping = {}
            for k, m in enumerate(msgs):
                ts = (t + timedelta(minutes=7 * k)).timestamp()
                mapping[f"u{k}"] = {"message": {"author": {"role": "user"}, "create_time": ts, "content": {"parts": [m]}}}
                mapping[f"a{k}"] = {"message": {"author": {"role": "assistant"}, "create_time": ts + 30,
                                                "content": {"parts": [random.choice(ASSIST)]}}}
            convs.append({"title": f"chat {d+1}", "mapping": mapping})
        json.dump(convs, open(f"{out}/exports/{pid}.json", "w"))
    import csv
    for name, rows in [("ema.csv", ema), ("truth.csv", truth)]:
        with open(f"{out}/{name}", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"simulated {n} persons x {days} days -> {out}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=60); a.add_argument("--days", type=int, default=14)
    a.add_argument("--seed", type=int, default=2026); a.add_argument("--out", default="demo/data")
    main(**vars(a.parse_args()))
