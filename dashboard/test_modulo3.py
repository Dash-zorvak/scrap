import sqlite3
import pandas as pd
import sys
sys.path.insert(0, "/Users/pro/Downloads/scrapeo-social/dashboard")
from config import *

# ── FACEBOOK TEST ──────────────────────────────────────────
conn = sqlite3.connect(FACEBOOK_TEST_DB)
df = pd.read_sql("""
    SELECT post_id, page_name, created_time, message,
           likes_count, loves_count, hahas_count, sads_count,
           angrys_count, comments_count
    FROM fb_posts
    WHERE created_time IS NOT NULL
""", conn)

df['total_reacciones'] = (df['likes_count'] + df['loves_count'] +
                           df['hahas_count'] + df['sads_count'] +
                           df['angrys_count'])
df['indice_amor']     = df['loves_count'] / df['total_reacciones'].replace(0,1)
df['indice_humor']    = df['hahas_count'] / df['total_reacciones'].replace(0,1)
df['indice_tristeza'] = df['sads_count']  / df['total_reacciones'].replace(0,1)
df['indice_enojo']    = df['angrys_count']/ df['total_reacciones'].replace(0,1)
df['engagement_total']= df['total_reacciones'] + df['comments_count']
df['score_emocional'] = df['indice_amor'] - df['indice_tristeza'] - df['indice_enojo']
df['plataforma']      = 'facebook'

df.to_sql('fb_engagement', conn, if_exists='replace', index=False)
print(f"FB engagement guardado: {len(df)} posts")
print(f"Score emocional promedio: {df['score_emocional'].mean():.3f}")
print(f"Indice enojo promedio: {df['indice_enojo'].mean():.3f}")

# ── TIKTOK TEST ────────────────────────────────────────────
conn_tk = sqlite3.connect(TIKTOK_TEST_DB)
df_tk = pd.read_sql("""
    SELECT id, account_id, description, created_at,
           views, likes, shares, favorites_count, comments_count
    FROM videos
""", conn_tk)

df_tk['engagement_total']  = (df_tk['likes'] + df_tk['shares'] +
                               df_tk['comments_count'] + df_tk['favorites_count'])
df_tk['engagement_rate']   = df_tk['engagement_total'] / df_tk['views'].replace(0,1)
df_tk['indice_viralidad']  = df_tk['shares'] / df_tk['views'].replace(0,1)
df_tk['score_engagement']  = df_tk['engagement_rate']
df_tk['page_name'] = df_tk['account_id'].map({1:'Alcaldía Santa Ana', 3:'Gustavo Acevedo'})
df_tk['plataforma'] = 'tiktok'

df_tk.to_sql('tiktok_engagement', conn_tk, if_exists='replace', index=False)
print(f"TK engagement guardado: {len(df_tk)} videos")
print(f"Engagement rate promedio: {df_tk['engagement_rate'].mean()*100:.2f}%")
conn.close()
conn_tk.close()
