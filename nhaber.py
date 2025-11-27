#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import feedparser
from rich.console import Console
from rich.table import Table
from rich import box
import logging
import warnings
import time

warnings.filterwarnings("ignore")

"""
PROJE: Lojistik İstihbarat Ajanı (v7.5 - Timestamp)
YENİLİK: Haberlere tarih sütunu eklendi.
FORMAT: Gün/Ay (Örn: 27/11)
"""

def fetch_intel():
    console = Console()
    console.print("\n[bold cyan]🌍 KÜRESEL İSTİHBARAT MASASI[/bold cyan]")
    
    # --- KAYNAK AYARLARI ---
    sources = [
        {"name": "gCaptain", "url": "https://gcaptain.com/feed/", "tag": "DENİZCİLİK", "color": "blue", "scan_limit": 10, "show_limit": 2},
        {"name": "FreightWaves", "url": "https://www.freightwaves.com/feed", "tag": "TEDARİK", "color": "magenta", "scan_limit": 8, "show_limit": 2},
        {"name": "OilPrice", "url": "https://oilprice.com/rss/main", "tag": "ENERJİ", "color": "red", "scan_limit": 6, "show_limit": 1},
        {"name": "CNBC World", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362", "tag": "EKONOMİ", "color": "green", "scan_limit": 5, "show_limit": 1}
    ]

    # --- KELİME FİLTRELERİ ---
    risk_keywords = ["strike", "war", "attack", "fire", "sink", "houthi", "delay", "crash", "sanction", "ban", "crisis", "conflict", "tariff", "collision"]
    cargo_keywords = ["soybean", "grain", "lng", "oil", "container", "vessel", "freight", "iron ore", "coal", "wheat", "export"]
    money_keywords = ["profit", "surge", "record", "deal", "growth", "boom", "dividend", "buy"]

    try:
        # --- TABLO TASARIMI ---
        table = Table(
            box=box.SQUARE,
            show_lines=True,
            header_style="bold white on dark_blue",
            expand=True
        )
        
        # SÜTUNLAR
        table.add_column("Tarih", justify="center", style="cyan dim", width=8)
        table.add_column("Kaynak", justify="center", style="bold", width=12)
        table.add_column("Kategori", justify="center", style="dim", width=10)
        table.add_column("İstihbarat Başlığı", ratio=1)

        with console.status("[bold green]Veri hücreleri ve tarihler işleniyor...[/bold green]", spinner="dots"):
            
            total_alerts = 0
            
            for source in sources:
                try:
                    feed = feedparser.parse(source["url"])
                    shown_neutral = 0
                    
                    for i, entry in enumerate(feed.entries):
                        if i >= source["scan_limit"]: break
                        
                        title = entry.title
                        title_lower = title.lower()

                        # --- TARİH FORMATLAMA ---
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            date_str = time.strftime("%d/%m", entry.published_parsed)
                        else:
                            date_str = "-"

                        # --- ANALİZ ---
                        is_important = False
                        icon = "•"
                        color_style = "white"
                        
                        if any(w in title_lower for w in risk_keywords):
                            icon = "⚠"
                            color_style = "bold red"
                            is_important = True
                        elif any(w in title_lower for w in cargo_keywords):
                            icon = "📦"
                            color_style = "bold yellow"
                            is_important = True
                        elif any(w in title_lower for w in money_keywords):
                            icon = "💰"
                            color_style = "bold green"
                            is_important = True

                        # --- GÖSTERİM KARARI ---
                        if is_important:
                            total_alerts += 1
                        else:
                            if shown_neutral >= source["show_limit"]: continue
                            shown_neutral += 1
                            if len(title) > 80: title = title[:77] + "..."

                        # --- HÜCRELERİ DOLDUR ---
                        src_cell = f"[{source['color']}]{source['name']}[/{source['color']}]"
                        title_cell = f"[{color_style}]{icon} {title}[/{color_style}]"
                        
                        table.add_row(date_str, src_cell, source["tag"], title_cell)

                except Exception as e:
                    table.add_row("-", source["name"], "HATA", str(e))

        console.print(table)
        
        if total_alerts > 0:
            console.print(f"[dim]Dipnot: Tarama sonucunda {total_alerts} adet kritik sinyal yakalandı.[/dim]\n", justify="right")

    except Exception as e:
        console.print(f"[bold red]Sistem Hatası:[/bold red] {e}")

if __name__ == "__main__":
    fetch_intel()
