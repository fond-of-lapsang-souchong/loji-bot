#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yfinance as yf
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import csv
import os
import sys
import logging
import warnings
from datetime import datetime

# --- YFINANCE GÜRÜLTÜSÜNÜ SUSTURMA ---
warnings.simplefilter(action='ignore', category=FutureWarning)

"""
PROJE: Lojistik İstihbarat Botu (v5.1 - Black Box Edition)
AÇIKLAMA: Küresel navlun, enerji ve tedarik zinciri verilerini takip eden,
          yorumlayan ve loglayan terminal tabanlı bir araç.
YAZAR: [Adın Soyadın]
"""

FILE_NAME = "lojistik_log.csv"
LOG_FILE = "lojistik_hata.log"

# --- LOG AYARLARI ---
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def save_to_csv(data_dict):
    """Verileri CSV dosyasına zaman damgasıyla kaydeder."""
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
    """Geçmiş kayıtları okur ve tablo olarak basar."""
    console = Console()
    if not os.path.isfile(FILE_NAME):
        console.print("[bold red]Henüz kayıtlı geçmiş veri yok![/bold red]")
        return
    try:
        table = Table(title="📜 Lojistik Kayıt Defteri", box=box.SIMPLE_HEAD)
        with open(FILE_NAME, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            # Dosya boşsa veya sadece başlık varsa hata vermemesi için kontrol
            try:
                headers = next(reader)
            except StopIteration:
                console.print("[dim]Dosya boş.[/dim]")
                return

            for h in headers: table.add_column(h, style="cyan")
            rows = list(reader)
            for row in rows[-10:]: table.add_row(*row)
        console.print(table)
    except Exception as e:
        msg = f"Geçmiş Okuma Hatası: {e}"
        console.print(f"[bold red]{msg}[/bold red]")
        logging.error(msg)

def generate_range_bar(data_list, width=10):
    """Fiyatın 14 günlük periyottaki konumunu çizer."""
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
            else:
                bar += "[dim]─[/dim]"
        return bar
    except Exception as e:
        logging.error(f"Grafik Çizim Hatası: {e}")
        return "[dim]ERROR[/dim]"

def analyze_risks(data):
    """Verileri çapraz sorgulayıp tehlike veya fırsat sinyali üretir."""
    console = Console()
    alerts = []

    try:
        # 1. MAKAS ANALİZİ (Petrol vs Maersk)
        
        oil_closes = data['Close']['CL=F'].dropna().tolist()
        oil_change = ((oil_closes[-1] - oil_closes[-2]) / oil_closes[-2]) * 100
        
        maersk_closes = data['Close']['AMKBY'].dropna().tolist()
        maersk_change = ((maersk_closes[-1] - maersk_closes[-2]) / maersk_closes[-2]) * 100

        if oil_change > 1.0 and maersk_change < 0.5:
            alerts.append(f"[bold red]⚠ MARJ BASKISI:[/bold red] Petrol artıyor (+%{oil_change:.1f}), ama Armatör hissesi tepki vermiyor.")

        # 2. RESESYON SİNYALİ (BDRY Çöküşü)
        bdry_closes = data['Close']['BDRY'].dropna().tolist()
        bdry_avg_14 = sum(bdry_closes) / len(bdry_closes)
        bdry_current = bdry_closes[-1]

        if bdry_current < (bdry_avg_14 * 0.95):
             alerts.append(f"[bold yellow]📉 RESESYON RİSKİ:[/bold yellow] Hammadde endeksi (BDRY) ortalamanın altında.")

        # 3. FIRSAT SİNYALİ (ZIM Aşırı Satış)
        zim_closes = data['Close']['ZIM'].dropna().tolist()
        if zim_closes[-1] <= min(zim_closes):
            alerts.append(f"[bold green]💰 ALIM FIRSATI:[/bold green] ZIM son 14 günün en dibinde.")

    except Exception as e:
        msg = f"Analiz Modülü Hatası (Veri eksik olabilir): {e}"
        # Analiz hatası kritik değildir, logla ve geç
        logging.error(msg) 

    if alerts:
        console.print(Panel("\n".join(alerts), title="🧠 YAPAY ZEKA ANALİZİ", border_style="red", expand=False))
    else:
        console.print("\n[dim green]✔ Piyasa analiz edildi: Stabil.[/dim green]")

def get_logistics_dashboard():
    console = Console()
    console.print("\n[bold cyan]📡 KÜRESEL LOJİSTİK İSTİHBARAT AĞI v5.1 (Black Box)[/bold cyan]")
    
    tickers_info = {
        "BDRY":  "Kuru Yük",
        "ZIM":   "Konteyner",
        "AMKBY": "Maersk",
        "FDX":   "FedEx", 
        "CL=F":  "Petrol"
    }
    
    try:
        # Veri Çekme (Hata olursa loglayacak ve duracak)
        data = yf.download(list(tickers_info.keys()), period="14d", progress=False, auto_adjust=False)
        
        # Eğer veri boş dönerse (İnternet yoksa vb.)
        if data.empty:
            raise ValueError("Yahoo Finance veri döndürmedi. İnternet bağlantınızı kontrol edin.")

        # Tablo Oluşturma
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
                
                if series.empty:
                    raise ValueError("Boş Veri")

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
            except Exception as e:
                logging.error(f"{ticker} verisi işlenirken hata: {e}")
                table.add_row(ticker, "N/A", "-", "HATA", desc)

        console.print(table)
        
        analyze_risks(data)

        if save_to_csv(current_values):
            console.print(f"[dim]Log güncellendi.[/dim]")

    except Exception as e:
        msg = f"Kritik Program Hatası: {e}"
        console.print(f"[bold red]{msg}[/bold red]")
        logging.critical(msg)

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "log":
            show_history()
        else:
            get_logistics_dashboard()
    except KeyboardInterrupt:
        print("\n[dim]Çıkış yapıldı.[/dim]")
