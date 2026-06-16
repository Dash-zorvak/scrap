import sqlite3
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *

# Clasificador por reglas (rápido, sin ML)
positivos = ['gracias','excelente','buen trabajo','progresa',
             'bendicion','felicitaciones','bien','bravo','orgullo']
negativos = ['mentira','corrupto','abandono','vergüenza','burla',
             'nada','peor','incompleta','prometieron','pura pantalla',
             'show','nunca','siguen igual','baches','roto','basura',
             'inutil','nefasto','robando','enojo','mal','terrible',
             'abandonado','promesas','incumplida','lleva años']

def clasificar(texto):
    if not texto: return 'NEU', 0.5
    t = texto.lower()
    pos = sum(1 for p in positivos if p in t)
    neg = sum(1 for p in negativos if p in t)
    if neg > pos: return 'NEG', min(0.95, 0.5 + neg*0.15)
    if pos > neg: return 'POS', min(0.95, 0.5 + pos*0.15)
    return 'NEU', 0.5

conn = sqlite3.connect(FACEBOOK_TEST_DB)
df_c = pd.read_sql(
    "SELECT comment_id, post_id, message FROM fb_comments WHERE message IS NOT NULL",
    conn
)
df_c[['label','conf']] = df_c['message'].apply(
    lambda x: pd.Series(clasificar(x))
)

resultados = []
for post_id, grupo in df_c.groupby('post_id'):
    total = len(grupo)
    pct_pos = (grupo['label']=='POS').sum() / total * 100
    pct_neg = (grupo['label']=='NEG').sum() / total * 100
    pct_neu = (grupo['label']=='NEU').sum() / total * 100
    score   = (pct_pos - pct_neg) / 100
    neg_idx = grupo[grupo['label']=='NEG']['conf'].idxmax() if (grupo['label']=='NEG').any() else None
    pos_idx = grupo[grupo['label']=='POS']['conf'].idxmax() if (grupo['label']=='POS').any() else None
    resultados.append({
        'post_id': post_id,
        'total_comentarios': total,
        'pct_positivo': pct_pos,
        'pct_negativo': pct_neg,
        'pct_neutral':  pct_neu,
        'score_sentimiento': score,
        'comentario_mas_negativo': grupo.loc[neg_idx,'message'][:150] if neg_idx else '',
        'comentario_mas_positivo': grupo.loc[pos_idx,'message'][:150] if pos_idx else ''
    })

df_sent = pd.DataFrame(resultados)
df_sent.to_sql('fb_sentimiento', conn, if_exists='replace', index=False)
print(f"Sentimiento guardado: {len(df_sent)} posts")
print(f"Score sentimiento promedio: {df_sent['score_sentimiento'].mean():.3f}")
print(f"% negativo promedio: {df_sent['pct_negativo'].mean():.1f}%")

# TikTok sentimiento
conn_tk = sqlite3.connect(TIKTOK_TEST_DB)
df_tk_c = pd.read_sql(
    "SELECT id, video_id, text FROM comments WHERE text IS NOT NULL",
    conn_tk
)
df_tk_c[['label','conf']] = df_tk_c['text'].apply(
    lambda x: pd.Series(clasificar(x))
)

resultados_tk = []
for vid_id, grupo in df_tk_c.groupby('video_id'):
    total = len(grupo)
    pct_pos = (grupo['label']=='POS').sum() / total * 100
    pct_neg = (grupo['label']=='NEG').sum() / total * 100
    pct_neu = (grupo['label']=='NEU').sum() / total * 100
    score   = (pct_pos - pct_neg) / 100
    neg_idx = grupo[grupo['label']=='NEG']['conf'].idxmax() if (grupo['label']=='NEG').any() else None
    pos_idx = grupo[grupo['label']=='POS']['conf'].idxmax() if (grupo['label']=='POS').any() else None
    resultados_tk.append({
        'post_id': vid_id,
        'total_comentarios': total,
        'pct_positivo': pct_pos,
        'pct_negativo': pct_neg,
        'pct_neutral':  pct_neu,
        'score_sentimiento': score,
        'comentario_mas_negativo': grupo.loc[neg_idx,'text'][:150] if neg_idx else '',
        'comentario_mas_positivo': grupo.loc[pos_idx,'text'][:150] if pos_idx else ''
    })

df_sent_tk = pd.DataFrame(resultados_tk)
df_sent_tk.to_sql('tiktok_sentimiento', conn_tk, if_exists='replace', index=False)
print(f"TK Sentimiento guardado: {len(df_sent_tk)} videos")
print(f"Score sentimiento TK promedio: {df_sent_tk['score_sentimiento'].mean():.3f}")
conn.close()
conn_tk.close()
