#!/usr/bin/env python3
"""
TikTok Login Helper - Captura cookies de sesión manualmente
Uso: python scripts/tt_login.py
"""
import sys
sys.path.insert(0, str(__file__).parent.parent)

from src.tiktok_scraper.bruteforce_scraper import login_and_save_cookies

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TikTok Login - Captura cookies de sesión")
    parser.add_argument("--cookies", default="tiktok_cookies.json")
    parser.add_argument("--user", default="alcaldiasa")
    args = parser.parse_args()
    login_and_save_cookies(args.cookies, args.user)
