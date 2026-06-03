#!/usr/bin/env python3
"""
Comprehensive NLP analysis of Ivan Cepeda's Colombian government plan 2026-2030.
Sections 1-7 as specified.
"""

import os
import sys
import re
import json
import warnings
import subprocess
warnings.filterwarnings("ignore")

# ─── PATHS ────────────────────────────────────────────────────────────────────
PDF_PATH = r"C:\Users\David.Munoz\Downloads\programa-gobierno-2026-2030.pdf"
OUT_DIR  = r"C:\output\cepeda_analysis"
os.makedirs(OUT_DIR, exist_ok=True)

# ─── AUTO-INSTALL HELPER ──────────────────────────────────────────────────────
def ensure(pkg, import_name=None):
    name = import_name or pkg
    try:
        __import__(name)
    except ImportError:
        print(f"  Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

for pkg, imp in [
    ("pymupdf", "fitz"), ("nltk", None), ("spacy", None),
    ("scikit-learn", "sklearn"), ("gensim", None), ("wordcloud", None),
    ("matplotlib", None), ("seaborn", None), ("networkx", None),
    ("pyLDAvis", "pyLDAvis"), ("umap-learn", "umap"),
    ("pysentimiento", None), ("lexicalrichness", None),
]:
    ensure(pkg, imp)

# ─── IMPORTS ──────────────────────────────────────────────────────────────────
import fitz                                  # pymupdf
import nltk
import spacy
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import seaborn as sns
import networkx as nx
from collections import Counter
from itertools import combinations

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation, NMF
from wordcloud import WordCloud
from gensim.models import Word2Vec, FastText
from gensim.models.coherencemodel import CoherenceModel
from gensim import corpora

try:
    import pyLDAvis
    import pyLDAvis.lda_model as pyLDAvis_sklearn
    HAS_PYLDAVIS = True
except Exception:
    HAS_PYLDAVIS = False

try:
    from pysentimiento import create_analyzer
    HAS_PYSENTIMIENTO = True
except Exception:
    HAS_PYSENTIMIENTO = False

try:
    import umap
    HAS_UMAP = True
except Exception:
    HAS_UMAP = False

try:
    from lexicalrichness import LexicalRichness
    HAS_LR = True
except Exception:
    HAS_LR = False

# ─── NLTK DATA ────────────────────────────────────────────────────────────────
for resource in ["stopwords", "punkt", "averaged_perceptron_tagger", "punkt_tab"]:
    try:
        nltk.data.find(f"tokenizers/{resource}" if "punkt" in resource else f"corpora/{resource}")
    except LookupError:
        nltk.download(resource, quiet=True)

from nltk.corpus import stopwords as nltk_sw
from nltk.util import ngrams as nltk_ngrams

# ─── spaCy MODEL ──────────────────────────────────────────────────────────────
try:
    nlp = spacy.load("es_core_news_sm")
except OSError:
    print("Downloading spaCy es_core_news_sm...")
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "es_core_news_sm", "-q"])
    nlp = spacy.load("es_core_news_sm")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 1 — TEXT EXTRACTION & CLEANING
# ════════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("SECTION 1 — TEXT EXTRACTION & CLEANING")
print("═"*60)

doc_pdf = fitz.open(PDF_PATH)
pages_raw = []
for i, page in enumerate(doc_pdf):
    text = page.get_text("text")
    pages_raw.append(text)

full_raw = "\n".join(pages_raw)
with open(os.path.join(OUT_DIR, "raw_text.txt"), "w", encoding="utf-8") as f:
    f.write(full_raw)
print(f"Extracted {len(pages_raw)} pages.")

# Stopwords
base_sw = set(nltk_sw.words("spanish"))
custom_sw = {
    "así","más","será","solo","puede","debe","cada","través","mediante",
    "tanto","bien","hacer","tener","parte","también","sino","ante",
    "desde","hacia","entre","sobre","donde","cual","cuales","este",
    "esta","estos","estas","ese","esa","esos","esas","aquel","aquella",
    "aquellos","aquellas","uno","una","unos","unas","ser","estar",
    "haber","hay","han","son","sus","del","las","los","les","nos",
    "les","como","pero","para","por","con","sin","todo","todos",
    "toda","todas","mismo","misma","mismos","mismas","muy","cuando",
    "quien","quienes","que","qué","cual","cuál","donde","cómo",
    "porque","si","ya","más","aún","solo","sólo","colombia","colombiano",
    "colombiana","colombianos","colombianas","gobierno","nacional","país",
    "público","pública","años","año","mil","millones","deben","hacer",
}
STOPWORDS = base_sw | custom_sw

def clean_text(text):
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"[0-9]+", " ", text)
    text = re.sub(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

pages_clean = [clean_text(p) for p in pages_raw]

# Tokenize + lemmatize per page
nlp.max_length = 2_000_000
pages_tokens = []  # list of token lists per page
for i, pg in enumerate(pages_clean):
    doc_spacy = nlp(pg[:100_000])  # cap to avoid memory issues
    tokens = [
        token.lemma_ for token in doc_spacy
        if token.is_alpha
        and token.lemma_.lower() not in STOPWORDS
        and len(token.lemma_) > 2
    ]
    pages_tokens.append(tokens)

all_tokens = [t for pg in pages_tokens for t in pg]
total_words   = len(all_tokens)
unique_words  = len(set(all_tokens))
avg_per_page  = total_words / max(len(pages_tokens), 1)

print(f"Total words (after cleaning/lemma): {total_words:,}")
print(f"Unique words: {unique_words:,}")
print(f"Avg words/page: {avg_per_page:.1f}")

clean_corpus = " ".join(all_tokens)
with open(os.path.join(OUT_DIR, "clean_tokens.txt"), "w", encoding="utf-8") as f:
    f.write(clean_corpus)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 2 — FREQUENCY ANALYSIS
# ════════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("SECTION 2 — FREQUENCY ANALYSIS")
print("═"*60)

freq = Counter(all_tokens)

# ── Word cloud ──
print("Generating word cloud...")
wc = WordCloud(
    width=1600, height=900, background_color="white",
    colormap="tab20", max_words=200,
    collocations=False
).generate_from_frequencies(freq)
wc.to_file(os.path.join(OUT_DIR, "wordcloud.png"))
print("  Saved wordcloud.png")

def hbar(data, title, filename, color="steelblue", value_labels=True):
    labels, values = zip(*data)
    fig, ax = plt.subplots(figsize=(12, max(6, len(labels)*0.4)))
    bars = ax.barh(range(len(labels)), values, color=color)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("Frequency")
    if value_labels:
        for bar, v in zip(bars, values):
            ax.text(bar.get_width()+0.3, bar.get_y()+bar.get_height()/2,
                    str(v), va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, filename), dpi=150)
    plt.close()
    print(f"  Saved {filename}")

# ── Top 40 unigrams
top40 = freq.most_common(40)
hbar(top40[::-1], "Top 40 Unigrams", "top40_unigrams.png")

# ── Bigrams
raw_bigrams = list(nltk_ngrams(all_tokens, 2))
bigram_freq = Counter(raw_bigrams).most_common(25)
top25_bg = [(" ".join(b), c) for b, c in bigram_freq]
hbar(top25_bg[::-1], "Top 25 Bigrams", "top25_bigrams.png", color="darkorange")

# ── Trigrams
raw_trigrams = list(nltk_ngrams(all_tokens, 3))
trigram_freq = Counter(raw_trigrams).most_common(20)
top20_tg = [(" ".join(t), c) for t, c in trigram_freq]
hbar(top20_tg[::-1], "Top 20 Trigrams", "top20_trigrams.png", color="seagreen")

# ── Quadgrams
raw_quadgrams = list(nltk_ngrams(all_tokens, 4))
quad_freq = Counter(raw_quadgrams).most_common(10)
top10_qg = [(" ".join(q), c) for q, c in quad_freq]
hbar(top10_qg[::-1], "Top 10 Quadgrams", "top10_quadgrams.png", color="mediumpurple")

# ── Zipf's law
print("Plotting Zipf's law...")
ranks  = np.arange(1, len(freq)+1)
counts = np.array([c for _, c in freq.most_common()])
fig, ax = plt.subplots(figsize=(8, 5))
ax.loglog(ranks, counts, "b.", markersize=2)
# Fit line
log_r = np.log(ranks[:500])
log_c = np.log(counts[:500])
m, b = np.polyfit(log_r, log_c, 1)
ax.loglog(ranks[:500], np.exp(b)*ranks[:500]**m, "r-", label=f"slope={m:.2f}")
ax.set_xlabel("Rank (log)")
ax.set_ylabel("Frequency (log)")
ax.set_title("Zipf's Law Plot")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "zipf_law.png"), dpi=150)
plt.close()
print("  Saved zipf_law.png")

# ── Lexical richness
if HAS_LR:
    try:
        lex = LexicalRichness(clean_corpus)
        ttr  = lex.ttr
        print(f"Type-Token Ratio (TTR): {ttr:.4f}")
        try:
            mtld = lex.mtld(threshold=0.72)
            print(f"MTLD: {mtld:.2f}")
        except Exception:
            mtld = None
        with open(os.path.join(OUT_DIR, "lexical_richness.txt"), "w") as f:
            f.write(f"TTR: {ttr:.4f}\nMTLD: {mtld}\n")
    except Exception as e:
        print(f"  Lexical richness skipped: {e}")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 3 — TOPIC MODELING
# ════════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("SECTION 3 — TOPIC MODELING")
print("═"*60)

# Build per-page documents (non-empty pages only)
page_docs = [" ".join(toks) for toks in pages_tokens if len(toks) > 10]
N_TOPICS  = 7

# ── LDA
print("Training LDA...")
cv = CountVectorizer(max_df=0.90, min_df=2, max_features=5000)
dtm = cv.fit_transform(page_docs)
lda = LatentDirichletAllocation(n_components=N_TOPICS, random_state=42,
                                max_iter=20, learning_method="batch")
lda.fit(dtm)

feature_names = cv.get_feature_names_out()
TOPIC_LABELS = {
    0: "Economy & Finance",
    1: "Human Rights & Justice",
    2: "Peace & Territory",
    3: "Environment & Land",
    4: "Health & Social Policy",
    5: "Education & Culture",
    6: "Institutions & Governance",
}
print("\nLDA Topics:")
lda_topic_words = {}
for i, comp in enumerate(lda.components_):
    top15 = [feature_names[j] for j in comp.argsort()[-15:][::-1]]
    lda_topic_words[i] = top15
    label = TOPIC_LABELS.get(i, f"Topic {i}")
    print(f"  {label}: {', '.join(top15[:8])}")

# ── NMF
print("Training NMF...")
tfidf_v = TfidfVectorizer(max_df=0.90, min_df=2, max_features=5000)
tfidf_m = tfidf_v.fit_transform(page_docs)
nmf = NMF(n_components=N_TOPICS, random_state=42, max_iter=400)
nmf.fit(tfidf_m)

nmf_fn = tfidf_v.get_feature_names_out()
print("\nNMF Topics:")
for i, comp in enumerate(nmf.components_):
    top15 = [nmf_fn[j] for j in comp.argsort()[-15:][::-1]]
    label = TOPIC_LABELS.get(i, f"Topic {i}")
    print(f"  {label}: {', '.join(top15[:8])}")

# ── Topic distribution chart
lda_dist = lda.transform(dtm)
topic_avgs = lda_dist.mean(axis=0)
fig, ax = plt.subplots(figsize=(10, 5))
colors = cm.tab10(np.linspace(0, 1, N_TOPICS))
ax.bar([TOPIC_LABELS.get(i, f"T{i}") for i in range(N_TOPICS)],
       topic_avgs, color=colors)
ax.set_title("LDA Topic Distribution Across Document", fontsize=12, fontweight="bold")
ax.set_ylabel("Average Weight")
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "lda_topic_distribution.png"), dpi=150)
plt.close()
print("Saved lda_topic_distribution.png")

# ── pyLDAvis
if HAS_PYLDAVIS:
    try:
        panel = pyLDAvis_sklearn.prepare(lda, dtm, cv, mds="mmds")
        pyLDAvis.save_html(panel, os.path.join(OUT_DIR, "lda_interactive.html"))
        print("Saved lda_interactive.html")
    except Exception as e:
        print(f"  pyLDAvis skipped: {e}")

# ── Gensim coherence
try:
    tokenized_docs = [d.split() for d in page_docs]
    dictionary = corpora.Dictionary(tokenized_docs)
    corpus_g   = [dictionary.doc2bow(d) for d in tokenized_docs]
    coh_lda = CoherenceModel(
        topics=[[w for w in lda_topic_words[i]] for i in range(N_TOPICS)],
        texts=tokenized_docs, dictionary=dictionary, coherence="c_v"
    )
    lda_coh = coh_lda.get_coherence()
    print(f"LDA Coherence (c_v): {lda_coh:.4f}")
    with open(os.path.join(OUT_DIR, "coherence_scores.txt"), "w") as f:
        f.write(f"LDA c_v coherence: {lda_coh:.4f}\n")
except Exception as e:
    print(f"  Coherence skipped: {e}")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 4 — SENTIMENT ANALYSIS
# ════════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("SECTION 4 — SENTIMENT ANALYSIS")
print("═"*60)

if HAS_PYSENTIMIENTO:
    print("Loading sentiment analyzer (robertuito)...")
    try:
        sent_analyzer = create_analyzer(task="sentiment", lang="es")
        emo_analyzer  = create_analyzer(task="emotion",   lang="es")

        page_sentiments = []
        for i, pg in enumerate(pages_raw):
            chunk = pg[:512]
            if len(chunk.strip()) < 20:
                page_sentiments.append({"pos": 0, "neg": 0, "neu": 1})
                continue
            try:
                res = sent_analyzer.predict(chunk)
                scores = res.probas
                page_sentiments.append({
                    "pos": scores.get("POS", 0),
                    "neg": scores.get("NEG", 0),
                    "neu": scores.get("NEU", 0),
                })
            except Exception:
                page_sentiments.append({"pos": 0, "neg": 0, "neu": 1})

        pages_idx = list(range(1, len(page_sentiments)+1))
        pos_scores = [s["pos"] for s in page_sentiments]
        neg_scores = [s["neg"] for s in page_sentiments]
        neu_scores = [s["neu"] for s in page_sentiments]

        # Sentiment arc
        fig, ax = plt.subplots(figsize=(14, 5))
        ax.plot(pages_idx, pos_scores, color="green",  label="Positive", linewidth=1)
        ax.plot(pages_idx, neg_scores, color="red",    label="Negative", linewidth=1)
        ax.plot(pages_idx, neu_scores, color="gray",   label="Neutral",  linewidth=1, alpha=0.5)
        ax.set_xlabel("Page")
        ax.set_ylabel("Score")
        ax.set_title("Sentiment Arc Across Document", fontsize=12, fontweight="bold")
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, "sentiment_arc.png"), dpi=150)
        plt.close()
        print("Saved sentiment_arc.png")

        # Overall distribution
        overall = {"Positive": np.mean(pos_scores),
                   "Negative": np.mean(neg_scores),
                   "Neutral":  np.mean(neu_scores)}
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(overall.keys(), overall.values(),
               color=["green", "red", "gray"])
        ax.set_title("Overall Sentiment Distribution")
        ax.set_ylabel("Mean Score")
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, "sentiment_distribution.png"), dpi=150)
        plt.close()

        # Top 5 most positive / negative paragraphs
        paragraphs, para_scores_pos, para_scores_neg = [], [], []
        for pg in pages_raw:
            for para in pg.split("\n\n"):
                para = para.strip()
                if len(para) > 80:
                    try:
                        res = sent_analyzer.predict(para[:512])
                        paragraphs.append(para)
                        para_scores_pos.append(res.probas.get("POS", 0))
                        para_scores_neg.append(res.probas.get("NEG", 0))
                    except Exception:
                        pass

        with open(os.path.join(OUT_DIR, "top_paragraphs.txt"), "w", encoding="utf-8") as f:
            f.write("=== TOP 5 MOST POSITIVE PARAGRAPHS ===\n\n")
            for idx in np.argsort(para_scores_pos)[-5:][::-1]:
                f.write(f"[Score: {para_scores_pos[idx]:.3f}]\n{paragraphs[idx]}\n\n")
            f.write("=== TOP 5 MOST NEGATIVE PARAGRAPHS ===\n\n")
            for idx in np.argsort(para_scores_neg)[-5:][::-1]:
                f.write(f"[Score: {para_scores_neg[idx]:.3f}]\n{paragraphs[idx]}\n\n")
        print("Saved top_paragraphs.txt")

    except Exception as e:
        print(f"  Sentiment analysis error: {e}")
else:
    print("  pysentimiento not available — skipping sentiment analysis")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SEMANTIC ANALYSIS
# ════════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("SECTION 5 — SEMANTIC ANALYSIS")
print("═"*60)

sentences = [pg for pg in pages_tokens if len(pg) > 5]
print(f"Training Word2Vec on {len(sentences)} page-documents...")
w2v = Word2Vec(sentences=sentences, vector_size=100, window=5,
               min_count=2, workers=4, epochs=20, seed=42)

KEY_TERMS = ["paz", "economía", "justicia", "pobreza",
             "derecho", "tierra", "salud", "educación"]

sim_results = {}
with open(os.path.join(OUT_DIR, "word2vec_similarities.txt"), "w", encoding="utf-8") as f:
    for term in KEY_TERMS:
        vocab = w2v.wv.key_to_index
        # try exact match first, then stem match
        matched = term if term in vocab else None
        if matched is None:
            for w in vocab:
                if w.startswith(term[:4]):
                    matched = w
                    break
        if matched:
            similar = w2v.wv.most_similar(matched, topn=10)
            sim_results[term] = similar
            f.write(f"\nTop similar to '{term}' (matched: '{matched}'):\n")
            for w, s in similar:
                f.write(f"  {w}: {s:.3f}\n")
            print(f"  {term}: {[w for w,_ in similar[:5]]}")
        else:
            f.write(f"\n'{term}' not in vocabulary\n")
            print(f"  '{term}' not in vocab")

# ── Semantic similarity network
print("Building similarity network...")
all_key_words = list(w2v.wv.key_to_index.keys())[:300]
G = nx.Graph()
THRESHOLD = 0.65
for i, w1 in enumerate(all_key_words):
    for w2 in all_key_words[i+1:]:
        try:
            sim = w2v.wv.similarity(w1, w2)
            if sim > THRESHOLD:
                G.add_edge(w1, w2, weight=sim)
        except Exception:
            pass

if G.number_of_nodes() > 0:
    fig, ax = plt.subplots(figsize=(14, 10))
    pos = nx.spring_layout(G, seed=42, k=0.5)
    nx.draw_networkx(G, pos, ax=ax, node_size=20, font_size=6,
                     width=0.3, alpha=0.7, with_labels=True)
    ax.set_title(f"Semantic Similarity Network (threshold={THRESHOLD})", fontsize=12)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "semantic_network.png"), dpi=150)
    plt.close()
    print("Saved semantic_network.png")

# ── t-SNE / UMAP of embeddings
print("Plotting word embeddings...")
vocab_words = list(w2v.wv.key_to_index.keys())[:200]
vectors = np.array([w2v.wv[w] for w in vocab_words])

try:
    from sklearn.manifold import TSNE
    tsne = TSNE(n_components=2, random_state=42, perplexity=30)
    coords = tsne.fit_transform(vectors)
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.scatter(coords[:,0], coords[:,1], s=8, alpha=0.6)
    for i, word in enumerate(vocab_words[:80]):
        ax.annotate(word, (coords[i,0], coords[i,1]), fontsize=6, alpha=0.8)
    ax.set_title("t-SNE Word Embeddings")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "tsne_embeddings.png"), dpi=150)
    plt.close()
    print("Saved tsne_embeddings.png")
except Exception as e:
    print(f"  t-SNE failed: {e}")

# ── KWIC
with open(os.path.join(OUT_DIR, "kwic.txt"), "w", encoding="utf-8") as f:
    for term in KEY_TERMS:
        f.write(f"\n=== KWIC: '{term}' ===\n")
        count = 0
        for pg in pages_raw:
            for sent in re.split(r'[.!?]', pg):
                if term in sent.lower() and count < 5:
                    f.write(f"  ...{sent.strip()[:200]}...\n")
                    count += 1
                if count >= 5:
                    break
print("Saved kwic.txt")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 6 — STRUCTURAL & RHETORICAL ANALYSIS
# ════════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("SECTION 6 — STRUCTURAL & RHETORICAL ANALYSIS")
print("═"*60)

sentences_raw = []
for pg in pages_raw:
    for sent in re.split(r'[.!?]', pg):
        sent = sent.strip()
        if len(sent) > 10:
            sentences_raw.append(sent)

sent_lengths = [len(s.split()) for s in sentences_raw]
word_lengths  = [len(w) for pg in pages_raw for w in pg.split() if w.isalpha()]
avg_sent_len = np.mean(sent_lengths)
avg_word_len = np.mean(word_lengths)
print(f"Avg sentence length: {avg_sent_len:.1f} words")
print(f"Avg word length: {avg_word_len:.1f} chars")

# Legibilidad: Fernández Huerta (1959) — fórmula Flesch adaptada al español
# Referencia: Fernández Huerta, J. (1959). Medidas sencillas de lecturabilidad.
# Fórmula: 206.84 - 1.02*(palabras/oraciones) - 60*(sílabas/palabras)
# Escala: 0-30 muy difícil | 30-50 difícil | 50-60 algo difícil | 60-70 normal | 70+ fácil

def count_syllables_es(word):
    """Cuenta sílabas en español considerando diptongos."""
    word = word.lower()
    vowels   = "aeiouáéíóúü"
    diphthongs = {"ai","au","ei","eu","oi","ou","ia","ie","io","iu","ua","ue","ui","uo"}
    count, i = 0, 0
    while i < len(word):
        if word[i] in vowels:
            if i + 1 < len(word) and word[i:i+2] in diphthongs:
                count += 1
                i += 2
            else:
                count += 1
                i += 1
        else:
            i += 1
    return max(1, count)

all_words_raw   = [w for pg in pages_raw for w in pg.split() if w.isalpha()]
total_words_raw = len(all_words_raw)
total_sents_raw = len(sentences_raw)
total_syllables = sum(count_syllables_es(w) for w in all_words_raw)

ppo = total_words_raw / max(total_sents_raw, 1)   # palabras por oración
psp = total_syllables / max(total_words_raw, 1)    # sílabas por palabra

fh_score = 206.84 - 1.02 * ppo - 60 * psp
print(f"Fernández Huerta (español): {fh_score:.1f} / 100")
print(f"  → palabras/oración: {ppo:.1f} | sílabas/palabra: {psp:.2f}")

with open(os.path.join(OUT_DIR, "readability.txt"), "w") as f:
    f.write("LEGIBILIDAD — Fernández Huerta (1959)\n")
    f.write("Fórmula: 206.84 - 1.02*(pal/orac) - 60*(síl/pal)\n")
    f.write("Escala: 0-30 muy difícil | 30-50 difícil | 50-60 algo difícil | 60-70 normal\n\n")
    f.write(f"Índice Fernández Huerta:  {fh_score:.1f} / 100\n")
    f.write(f"Palabras por oración:     {ppo:.1f}\n")
    f.write(f"Sílabas por palabra:      {psp:.2f}\n")
    f.write(f"Longitud media oración:   {avg_sent_len:.1f} palabras\n")
    f.write(f"Longitud media palabra:   {avg_word_len:.1f} caracteres\n")

# Sentence length histogram
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(sent_lengths, bins=40, color="steelblue", edgecolor="white")
ax.set_xlabel("Words per Sentence")
ax.set_ylabel("Count")
ax.set_title("Sentence Length Distribution")
ax.axvline(avg_sent_len, color="red", linestyle="--", label=f"Mean={avg_sent_len:.1f}")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "sentence_length_hist.png"), dpi=150)
plt.close()
print("Saved sentence_length_hist.png")

# Sentence starters
starters = []
for s in sentences_raw:
    words = s.split()
    if len(words) >= 2:
        starters.append(" ".join(words[:2]).lower())
starter_freq = Counter(starters).most_common(20)
hbar(starter_freq[::-1], "Top 20 Sentence Starters", "sentence_starters.png", color="teal")

# Passive voice estimation (Spanish: ser/estar + past participle)
passive_pat = re.compile(
    r"\b(ser|es|son|fue|fueron|será|serán|sido|estar|está|están|estuvo|estuvieron)\b"
    r"\s+\w+[aeiou]d[ao]s?\b", re.IGNORECASE
)
passive_count = sum(len(passive_pat.findall(pg)) for pg in pages_raw)
total_sents   = len(sentences_raw)
print(f"Estimated passive constructions: {passive_count} / {total_sents} sentences = {100*passive_count/max(total_sents,1):.1f}%")

# Paragraph density heatmap (words per page)
words_per_page = [len(pg.split()) for pg in pages_raw]
side = int(np.ceil(np.sqrt(len(words_per_page))))
pad  = side*side - len(words_per_page)
heatmap_data = np.array(words_per_page + [0]*pad).reshape(side, side)
fig, ax = plt.subplots(figsize=(12, 10))
sns.heatmap(heatmap_data, ax=ax, cmap="YlOrRd", linewidths=0.5,
            annot=False, cbar_kws={"label": "Words per page"})
ax.set_title("Paragraph Density Heatmap (Words per Page)", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "density_heatmap.png"), dpi=150)
plt.close()
print("Saved density_heatmap.png")

# ── NER
print("Running NER...")
ner_entities = {"PERSON": [], "ORG": [], "GPE": [], "LOC": [], "LAW": []}
full_for_ner = full_raw[:500_000]  # cap for speed
ner_doc = nlp(full_for_ner)
for ent in ner_doc.ents:
    if ent.label_ in ner_entities:
        ner_entities[ent.label_].append(ent.text.strip())

for etype, entities in ner_entities.items():
    cnt = Counter(entities).most_common(20)
    if cnt:
        hbar(cnt[::-1], f"Top 20 {etype} Entities", f"ner_{etype.lower()}.png",
             color="cornflowerblue")
        print(f"  {etype}: {[e for e,_ in cnt[:5]]}")

# NER co-occurrence network
print("Building NER co-occurrence network...")
ner_G = nx.Graph()
for pg in pages_raw[:100]:
    pg_doc = nlp(pg[:5000])
    pg_ents = [e.text.strip() for e in pg_doc.ents
               if e.label_ in ("PERSON","ORG","GPE") and len(e.text) > 3]
    for e1, e2 in combinations(set(pg_ents), 2):
        if ner_G.has_edge(e1, e2):
            ner_G[e1][e2]["weight"] += 1
        else:
            ner_G.add_edge(e1, e2, weight=1)

# keep top edges
edges_sorted = sorted(ner_G.edges(data=True), key=lambda x: x[2]["weight"], reverse=True)[:80]
ner_sub = nx.Graph()
for u, v, d in edges_sorted:
    ner_sub.add_edge(u, v, weight=d["weight"])

if ner_sub.number_of_nodes() > 0:
    fig, ax = plt.subplots(figsize=(14, 10))
    pos = nx.spring_layout(ner_sub, seed=42)
    weights = [ner_sub[u][v]["weight"] for u, v in ner_sub.edges()]
    nx.draw_networkx(ner_sub, pos, ax=ax, node_size=30, font_size=6,
                     width=[w*0.3 for w in weights], alpha=0.8, with_labels=True)
    ax.set_title("Named Entity Co-occurrence Network", fontsize=12)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "ner_cooccurrence_network.png"), dpi=150)
    plt.close()
    print("Saved ner_cooccurrence_network.png")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 7 — THEMATIC DEEP DIVE
# ════════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("SECTION 7 — THEMATIC DEEP DIVE")
print("═"*60)

THEMATIC_DICTS = {
    "Economy": [
        "economía","económico","empleo","trabajo","inversión","producción",
        "empresa","industria","comercio","exportación","importación","pib",
        "crecimiento","mercado","fiscal","tributario","impuesto","ingreso",
        "salario","deuda","presupuesto","finanza","banco","crédito","inflación",
    ],
    "Human Rights": [
        "derecho","humano","libertad","dignidad","igualdad","discriminación",
        "justicia","víctima","violencia","protección","garantía","ddhh",
        "defensor","vulneración","reparación","verdad","memoria","mujer",
        "género","etnia","indígena","afrodescendiente","minorías",
    ],
    "Peace": [
        "paz","conflicto","acuerdo","negociación","cese","guerrilla","farc",
        "eln","reintegración","desmovilización","reconciliación","posconflicto",
        "reincorporación","diálogo","territorial","zonas","excombatiente",
    ],
    "Environment": [
        "ambiente","ambiental","ecosistema","biodiversidad","bosque","agua",
        "clima","cambio climático","sostenible","sostenibilidad","contaminación",
        "energía","renovable","páramo","deforestación","ríos","minería",
        "extractivismo","verde","carbono","emisiones",
    ],
    "Land Reform": [
        "tierra","reforma","agraria","campo","rural","campesino","latifundio",
        "territorio","catastro","titulación","restitución","despojo",
        "propietario","predio","hectárea","finca","agricultor","comunidad",
    ],
    "Health": [
        "salud","hospital","médico","enfermedad","pandemia","atención",
        "seguro","eps","sistema","cobertura","vacuna","medicamento",
        "nutrición","mortalidad","mental","farmacéutico","clínica",
    ],
    "Education": [
        "educación","escuela","universidad","estudiante","maestro","docente",
        "formación","conocimiento","ciencia","tecnología","investigación",
        "acceso","calidad","analfabetismo","cobertura","beca","aprendizaje",
    ],
    "Security": [
        "seguridad","crimen","delincuencia","policía","ejército","fuerza",
        "narcotráfico","droga","coca","cultivo","ilícito","delito","homicidio",
        "extorsión","secuestro","paramilitarismo","banda","criminal",
    ],
}

theme_counts = {theme: [] for theme in THEMATIC_DICTS}
for pg in pages_raw:
    pg_lower = pg.lower()
    for theme, keywords in THEMATIC_DICTS.items():
        count = sum(pg_lower.count(kw) for kw in keywords)
        theme_counts[theme].append(count)

# Save CSV
theme_df = pd.DataFrame(theme_counts)
theme_df.index.name = "page"
theme_df.to_csv(os.path.join(OUT_DIR, "theme_counts_per_page.csv"))

# Line plot: theme mentions across pages
fig, ax = plt.subplots(figsize=(16, 7))
colors = cm.tab10(np.linspace(0, 1, len(THEMATIC_DICTS)))
for (theme, counts), color in zip(theme_counts.items(), colors):
    smoothed = pd.Series(counts).rolling(5, min_periods=1).mean()
    ax.plot(range(1, len(counts)+1), smoothed, label=theme, color=color, linewidth=1.5)
ax.set_xlabel("Page")
ax.set_ylabel("Keyword Mentions (5-page rolling avg)")
ax.set_title("Thematic Mentions Across Document", fontsize=13, fontweight="bold")
ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "theme_mentions_timeline.png"), dpi=150)
plt.close()
print("Saved theme_mentions_timeline.png")

# Overall theme totals bar chart
theme_totals = {t: sum(c) for t, c in theme_counts.items()}
fig, ax = plt.subplots(figsize=(10, 5))
sorted_themes = sorted(theme_totals.items(), key=lambda x: x[1], reverse=True)
ax.bar([t for t, _ in sorted_themes], [v for _, v in sorted_themes],
       color=cm.tab10(np.linspace(0, 1, len(sorted_themes))))
ax.set_title("Total Theme Mentions in Document", fontsize=12, fontweight="bold")
ax.set_ylabel("Total Keyword Mentions")
plt.xticks(rotation=20, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "theme_totals.png"), dpi=150)
plt.close()
print("Saved theme_totals.png")

# Heatmap: themes vs page sections (10-page buckets)
n_buckets = max(1, len(pages_raw) // 10)
bucket_size = len(pages_raw) // n_buckets
hm_data = {}
for theme in THEMATIC_DICTS:
    buckets = []
    for i in range(n_buckets):
        bucket_pages = theme_counts[theme][i*bucket_size:(i+1)*bucket_size]
        buckets.append(sum(bucket_pages))
    hm_data[theme] = buckets

hm_df = pd.DataFrame(hm_data).T
hm_df.columns = [f"p{i*bucket_size+1}-{(i+1)*bucket_size}" for i in range(n_buckets)]
fig, ax = plt.subplots(figsize=(16, 6))
sns.heatmap(hm_df, ax=ax, cmap="YlOrRd", linewidths=0.5,
            annot=True, fmt="d", annot_kws={"size": 7})
ax.set_title("Theme Intensity Heatmap (10-page buckets)", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "theme_heatmap.png"), dpi=150)
plt.close()
print("Saved theme_heatmap.png")

# ─── FINAL SUMMARY ───────────────────────────────────────────────────────────
print("\n" + "═"*60)
print("ANALYSIS COMPLETE")
print("═"*60)
output_files = sorted(os.listdir(OUT_DIR))
print(f"Output files in {OUT_DIR}:")
for fn in output_files:
    size = os.path.getsize(os.path.join(OUT_DIR, fn))
    print(f"  {fn}  ({size/1024:.1f} KB)")
print(f"\nTotal files: {len(output_files)}")
