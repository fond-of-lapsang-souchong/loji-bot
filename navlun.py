#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yfinance as yf
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import asciichartpy
import pandas as pd
import feedparser
import csv
import os
import sys
import logging
import warnings
from datetime import datetime

warnings.simplefilter(action='ignore', category=FutureWarning)

"""
PROJE: Lojistik İstihbarat Botu (v7.0 - The Informant)
YENİLİK: RSS Haber Modülü. Lojistik dünyasındaki gelişmeleri (gCaptain) çeker.
         Kritik kelimeleri (Grev, Savaş, Kaza) tespit edip kırmızı ile vurgular.
"""

FILE_NAME = "lojistik_log.csv"
LOG_FILE = "lojistik_hata.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def save_to_csv(data_dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [now]
    headers = ["Tarih"]
    for ticker, val in data_dict.items():
        headers.append(ticker)
        row.append(f"{val:.2f}")
    try:
        file_exists = os.path.isfile(FILE_NAME)
        with open(FILE_NAME, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists: writer.writerow(headers)
            writer.writerow(row)
        return True
    except Exception as e:
        logging.error(f"CSV Kayıt Hatası: {e}")
        return False

def show_history():
    console = Console()
    if not os.path.isfile(FILE_NAME):
        console.print("[bold red]Kayıt yok![/bold red]")
        return
    try:
        df = pd.read_csv(FILE_NAME)
        if df.empty:
            console.print("[dim]Dosya boş.[/dim]")
            return
        table = Table(title="📜 Lojistik Kayıt Defteri", box=box.SIMPLE_HEAD)
        for col in df.columns: table.add_column(col, style="cyan")
        for index, row in df.tail(10).iloc[::-1].iterrows():
            row_list = [str(x) for x in row.tolist()]
            table.add_row(*row_list)
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Hata:[/bold red] {e}")

def show_charts():
    console = Console()
    if not os.path.isfile(FILE_NAME):
        console.print("[bold red]Veri yok![/bold red]")
        return
    try:
        df = pd.read_csv(FILE_NAME)
        if len(df) < 2:
            console.print("[bold yellow]⚠ Grafik için en az 2 veri lazım.[/bold yellow]")
            return
        columns_to_plot = {"BDRY":"blue", "ZIM":"cyan", "AMKBY":"magenta", "FDX":"green", "CL=F":"red"}
        console.print("\n[bold u]GEÇMİŞ PERFORMANS GRAFİKLERİ[/bold u]\n")
        for col, color_name in columns_to_plot.items():
            if col in df.columns:
                series = df[col].tolist()
                last_price = series[-1]
                console.print(f"[bold {color_name}]📈 {col} Trendi (Son: ${last_price:.2f})[/bold {color_name}]")
                config = {"height": 10, "format": "{:8.2f}"}
                if color_name == "blue": c = asciichartpy.blue
                elif color_name == "cyan": c = asciichartpy.cyan
                elif color_name == "red": c = asciichartpy.red
                elif color_name == "green": c = asciichartpy.green
                else: c = asciichartpy.default
                config["colors"] = [c]
                print(asciichartpy.plot(series, config))
                print("\n" + "-"*40 + "\n")
        console.print(f"[dim]Veri Aralığı: {df['Tarih'].iloc[0]} - {df['Tarih'].iloc[-1]}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Hata:[/bold red] {e}")

def generate_range_bar(data_list, width=10):
    if not data_list: return ""
    try:
        current = data_list[-1]
        low, high = min(data_list), max(data_list)
        if high == low: return "[dim]──●──[/dim]"
        pct = (current - low) / (high - low)
        idx = int(pct * (width - 1))
        bar = ""
        for i in range(width):
            if i == idx:
                if pct > 0.8: bar += "[red]●[/red]"
                elif pct < 0.2: bar += "[green]●[/green]"
                else: bar += "[yellow]●[/yellow]"
            else: bar += "[dim]─[/dim]"
        return bar
    except: return "[dim]ERR[/dim]"

# --- HABER MODÜLÜ ---
def fetch_logistics_news():
    console = Console()
    rss_url = "https://gcaptain.com/feed/" 
    
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        
        # 1. RİSK KELİMELERİ (KIRMIZI - Olay Odaklı)
        risk_keywords = ["strike", "attack", "war", "sink", "fire", "collision", "pirate", "houthi", "delay", "crash", "sanction", "ban"]
        
        # 2. YÜK & EMTİA KELİMELERİ (SARI - Para Odaklı)
        cargo_keywords = ["soybean", "grain", "wheat", "corn", "iron ore", "coal", "lng", "crude", "oil", "bunker", "container", "export", "import"]

        # 3. POZİTİF KELİMELER (YEŞİL - Şirket Odaklı)
        good_keywords = ["profit", "record", "growth", "deal", "new route", "upgrade", "dividend"]

        count = 0
        for entry in feed.entries:
            if count >= 5: break 
            
            title = entry.title
            published = entry.published_parsed
            date_str = f"{published.tm_mday}/{published.tm_mon}" if published else ""

            title_lower = title.lower()
            
            # --- RENK MANTIĞI ---
            if any(word in title_lower for word in risk_keywords):
                # Tehlike varsa KIRMIZI
                formatted_title = f"[bold red]⚠ {title}[/bold red]"
            
            elif any(word in title_lower for word in cargo_keywords):
                # Yük/Emtia hareketi varsa SARI (Ticari Fırsat)
                formatted_title = f"[bold yellow]💰 {title}[/bold yellow]"
                
            elif any(word in title_lower for word in good_keywords):
                # Şirket haberi varsa YEŞİL
                formatted_title = f"[bold green]✔ {title}[/bold green]"
            else:
                # Nötr haber
                formatted_title = f"[dim]{title}[/dim]"
            # ----------------------------------

            news_items.append(f"[cyan]{date_str}[/cyan] | {formatted_title}")
            count += 1
            
        if news_items:
            console.print(Panel("\n".join(news_items), title="📰 DENİZCİLİK & LOJİSTİK İSTİHBARATI", border_style="blue"))
        else:
            console.print("[dim]Haber akışı boş.[/dim]")

    except Exception as e:
        logging.error(f"Haber Modülü Hatası: {e}")
        console.print(f"[dim red]Haberler çekilemedi: {e}[/dim red]")

def analyze_risks(data):
    console = Console()
    alerts = []
    try:
        oil_closes = data['Close']['CL=F'].dropna().tolist()
        oil_change = ((oil_closes[-1] - oil_closes[-2]) / oil_closes[-2]) * 100
        maersk_closes = data['Close']['AMKBY'].dropna().tolist()
        maersk_change = ((maersk_closes[-1] - maersk_closes[-2]) / maersk_closes[-2]) * 100

        if oil_change > 1.0 and maersk_change < 0.5:
            alerts.append(f"[bold red]⚠ MARJ BASKISI:[/bold red] Petrol artıyor (+%{oil_change:.1f}), ama Armatör hissesi tepki vermiyor.")

        bdry_avg = data['Close']['BDRY'].mean()
        if data['Close']['BDRY'].iloc[-1] < (bdry_avg * 0.95):
             alerts.append(f"[bold yellow]📉 RESESYON RİSKİ:[/bold yellow] Hammadde endeksi ortalamanın altında.")

        zim_closes = data['Close']['ZIM'].dropna().tolist()
        if zim_closes[-1] <= min(zim_closes):
            alerts.append(f"[bold green]💰 ALIM FIRSATI:[/bold green] ZIM dipte.")

    except Exception as e:
        logging.error(f"Analiz Hatası: {e}")

    if alerts:
        console.print(Panel("\n".join(alerts), title="🧠 YAPAY ZEKA ANALİZİ", border_style="red", expand=False))

def get_logistics_dashboard():
    console = Console()
    console.print("\n[bold cyan]📡 KÜRESEL LOJİSTİK İSTİHBARAT AĞI v7.0 (The Informant)[/bold cyan]")
    
    tickers_info = {"BDRY": "Kuru Yük", "ZIM": "Konteyner", "AMKBY": "Maersk", "FDX": "FedEx", "CL=F": "Petrol"}
    
    try:
        data = yf.download(list(tickers_info.keys()), period="14d", progress=False, auto_adjust=False)
        if data.empty: raise ValueError("Veri yok.")
        
        fetch_logistics_news()
        print("")

        table = Table(box=box.SIMPLE, header_style="bold white on blue")
        table.add_column("Enstrüman", style="cyan bold")
        table.add_column("Fiyat", justify="right")
        table.add_column("Trend (14G)", justify="center")
        table.add_column("Değişim", justify="right")
        table.add_column("Etiket", style="dim italic")

        current_values = {}
        for ticker, desc in tickers_info.items():
            try:
                series = data['Close'][ticker].dropna()
                closes = series.tolist()
                price = closes[-1]
                prev = closes[-2]
                pct = ((price - prev) / prev) * 100
                current_values[ticker] = price
                r_bar = generate_range_bar(closes)
                if pct > 0: arrow = f"[green]▲ %{abs(pct):.2f}[/green]"
                elif pct < 0: arrow = f"[red]▼ %{abs(pct):.2f}[/red]"
                else: arrow = "[dim]• %0.00[/dim]"
                table.add_row(ticker, f"${price:.2f}", r_bar, arrow, desc)
            except: table.add_row(ticker, "N/A", "-", "HATA", desc)

        console.print(table)
        analyze_risks(data)
        if save_to_csv(current_values): console.print(f"[dim]Log güncellendi.[/dim]")

    except Exception as e:
        console.print(f"[bold red]Hata:[/bold red] {e}")
        logging.critical(f"Ana döngü hatası: {e}")

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "log": show_history()
            elif sys.argv[1] == "grafik": show_charts()
        else:
            get_logistics_dashboard()
    except KeyboardInterrupt:
        print("\n[dim]Çıkış.[/dim]")
