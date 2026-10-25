#!/usr/bin/env python3
"""
Scraper Multi-Marca y Multi-Retail: Samsung, LG e Hisense
Por tamaños: 43", 50", 55", 58", 60" y 65".
Asigna fecha y hora de verificación de precios y exporta a JSON y CSV.
"""

import sys
import os
import re
import json
import csv
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

TARGET_SIZES = [43, 50, 55, 58, 60, 65]
BRANDS = ['Samsung', 'LG', 'Hisense']

MESES_ES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

def get_fecha_formateada(dt: datetime) -> str:
    mes = MESES_ES[dt.month]
    hora_12 = dt.strftime("%I:%M %p")
    return f"{dt.day} de {mes} de {dt.year}, {hora_12}"

def parse_price(val) -> int:
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        cleaned = re.sub(r'[^\d]', '', val)
        if cleaned:
            return int(cleaned)
    return 0

def format_cop(val: int) -> str:
    return f"${val:,.0f}".replace(',', '.')

def parse_brand_item(title: str, raw_brand: str, price_val, url: str, store: str) -> Optional[Dict]:
    if not title:
        return None
    title_clean = title.strip()
    title_lower = title_clean.lower()

    if any(trigger in title_lower for trigger in ['proyector', 'cable hdmi', 'funda protectora']):
        return None
    first_two = ' '.join(title_lower.split()[:2])
    if any(trigger in first_two for trigger in ['soporte', 'instalación', 'instalacion', 'control', 'cable', 'antena', 'rack']):
        return None
    if not any(term in title_lower for term in ['televisor', 'tv', 'smart']):
        return None

    brand = None
    if raw_brand and 'samsung' in raw_brand.lower():
        brand = 'Samsung'
    elif raw_brand and 'lg' in raw_brand.lower():
        brand = 'LG'
    elif raw_brand and 'hisense' in raw_brand.lower():
        brand = 'Hisense'
    elif 'samsung' in title_lower:
        brand = 'Samsung'
    elif re.search(r'\blg\b', title_lower):
        brand = 'LG'
    elif 'hisense' in title_lower:
        brand = 'Hisense'

    if not brand or brand not in BRANDS:
        return None

    m_inch = re.search(r'(\d{2,3})\s*(?:\"|”|″|\'\'|\b(?:pulgadas?|pulg|in)\b)', title_clean, re.IGNORECASE)
    inches_num = None
    if m_inch:
        inches_num = int(m_inch.group(1))
    else:
        m_model = re.search(r'\b(?:UN|QN|QNED|OLED|UR|UT|DU|CU|AU|MRN|A[0-9])?(\d{2})[A-Z0-9]', title_clean)
        common_sizes = [24, 28, 32, 40, 42, 43, 48, 50, 55, 58, 60, 65, 70, 75, 77, 83, 85, 86, 98]
        if m_model and int(m_model.group(1)) in common_sizes:
            inches_num = int(m_model.group(1))

    if not inches_num or inches_num not in TARGET_SIZES:
        return None

    techs = []
    if re.search(r'\boled\b', title_lower):
        techs.append('OLED')
    elif re.search(r'\bqned\b', title_lower):
        techs.append('QNED')
    elif re.search(r'\bneo\s*qled\b', title_lower):
        techs.append('Neo QLED')
    elif re.search(r'\bqled\b', title_lower):
        techs.append('QLED')
    elif re.search(r'\bnanocell\b|\bnano\b', title_lower):
        techs.append('NanoCell')
    elif re.search(r'\bmini\s*led\b', title_lower):
        techs.append('Mini LED')
    elif re.search(r'\bcrystal\b', title_lower):
        techs.append('Crystal UHD')
    elif re.search(r'\bled\b', title_lower):
        techs.append('LED')

    if re.search(r'\b(4k|uhd|uhd4k|ultra\s*hd)\b', title_lower):
        techs.append('4K UHD')
    elif re.search(r'\b(full\s*hd|fhd|1080p)\b', title_lower):
        techs.append('Full HD')
    elif re.search(r'\bhd\b', title_lower):
        techs.append('HD')

    if 'google tv' in title_lower:
        techs.append('Google TV')
    elif 'vidaa' in title_lower:
        techs.append('VIDAA OS')
    elif 'tizen' in title_lower:
        techs.append('Tizen OS')
    elif 'webos' in title_lower:
        techs.append('webOS')
    elif 'smart' in title_lower:
        techs.append('Smart TV')

    if not techs:
        techs.append('Smart TV')

    tech_str = ', '.join(dict.fromkeys(techs))
    price_num = parse_price(price_val)
    if price_num < 100000:
        return None

    return {
        'tienda': store,
        'marca': brand,
        'pulgadas': f'{inches_num}"',
        'pulgadas_num': inches_num,
        'tecnologia': tech_str,
        'precio_final': price_num,
        'precio_formateado': format_cop(price_num),
        'titulo': title_clean,
        'enlace': url
    }

def run_scraper(headless: bool = True):
    ahora = datetime.now()
    fecha_str = get_fecha_formateada(ahora)
    logging.info(f"Iniciando extracción multi-marca (LG, Samsung, Hisense) | Verificación: {fecha_str}")

    all_items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        # 1. Falabella
        for brand in BRANDS:
            logging.info(f"[Falabella] Consultando {brand}...")
            url = f"https://www.falabella.com.co/falabella-co/search?Ntt=televisor+{brand.lower()}&sortBy=derived.price.search%2Casc"
            try:
                page.goto(url, wait_until='networkidle', timeout=30000)
                raw = page.locator('#__NEXT_DATA__').inner_text()
                d = json.loads(raw)
                for r in d.get('props', {}).get('pageProps', {}).get('results', []):
                    title = r.get('displayName')
                    raw_b = r.get('brandName') or r.get('brand')
                    prod_url = r.get('url') or ''
                    if prod_url and not prod_url.startswith('http'):
                        prod_url = f"https://www.falabella.com.co{prod_url}"
                    prices = r.get('prices', [])
                    active = [parse_price(pr['price'][0]) for pr in prices if not pr.get('crossed', False) and pr.get('price')]
                    best = min(active) if active else 0
                    parsed = parse_brand_item(title, raw_b, best, prod_url, "Falabella")
                    if parsed:
                        all_items.append(parsed)
            except Exception:
                pass

        # 2. Éxito: categorización por rangos de tamaño y marcas
        exito_urls = [
            "https://www.exito.com/tecnologia/televisores?category-2=televisores&brand=lg&brand=samsung&brand=hisense&rango-tamano-de-pantalla=40-a-43-pulgadas&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0",
            "https://www.exito.com/tecnologia/televisores?category-2=televisores&brand=lg&brand=samsung&brand=hisense&rango-tamano-de-pantalla=44-a-50-pulgadas&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0",
            "https://www.exito.com/tecnologia/televisores?category-2=televisores&brand=lg&brand=samsung&brand=hisense&rango-tamano-de-pantalla=51-a-60-pulgadas&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0",
            "https://www.exito.com/tecnologia/televisores?category-2=televisores&brand=lg&brand=samsung&brand=hisense&rango-tamano-de-pantalla=61-a-70-pulgadas&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0",
            "https://www.exito.com/s?q=televisor+58+pulgadas+samsung&sort=price_asc",
            "https://www.exito.com/s?q=televisor+60+pulgadas+lg&sort=price_asc",
            "https://www.exito.com/s?q=televisor+65+pulgadas+samsung&sort=price_asc",
            "https://www.exito.com/s?q=televisor+hisense&sort=price_asc"
        ]

        for u in exito_urls:
            try:
                page.goto(u, wait_until='domcontentloaded', timeout=25000)
                page.wait_for_timeout(2500)
                cards = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('article')).map(a => {
                        const link = a.querySelector('a');
                        const titleEl = a.querySelector('h3, [class*="productCard_productCard__name"], a[title]');
                        const brandEl = a.querySelector('[class*="productCard_productCard__brand"], [data-fs-product-card-brand]');
                        const priceEls = Array.from(a.querySelectorAll('[data-fs-price="true"], [class*="ProductPrice_container__price"], [class*="price_fs-price"]'));
                        const allText = a.innerText.split('\\n').map(t => t.trim()).filter(Boolean);
                        return {
                            title: titleEl ? (titleEl.innerText || titleEl.getAttribute('title') || '') : '',
                            brand: brandEl ? brandEl.innerText : '',
                            prices: priceEls.map(p => p.innerText.trim()).filter(Boolean),
                            allText: allText,
                            href: link ? link.href : ''
                        };
                    });
                }""")
                for c in cards:
                    title = c['title']
                    raw_b = c['brand']
                    all_text = c['allText']
                    if not title or 'patrocinado' in title.lower():
                        for line in all_text:
                            if 'televisor' in line.lower() or 'tv' in line.lower() or 'hisense' in line.lower() or 'samsung' in line.lower() or 'lg' in line.lower():
                                title = line
                                break
                    found_prices = [parse_price(p) for p in c['prices'] if parse_price(p) > 100000]
                    if not found_prices:
                        for line in all_text:
                            if '$' in line and not any(w in line.lower() for w in ['cuota', 'mes', 'seguro']):
                                val = parse_price(line)
                                if val > 100000:
                                    found_prices.append(val)
                    best = min(found_prices) if found_prices else 0
                    parsed = parse_brand_item(title, raw_b, best, c['href'], "Éxito")
                    if parsed:
                        all_items.append(parsed)
            except Exception:
                pass

        # 3. Jumbo
        for brand in ['samsung', 'lg', 'hisense']:
            url = f"https://www.jumbocolombia.com/co/televisores-y-audio/television/{brand}?order=OrderByPriceASC"
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(2500)
                cards_j = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a[href*="/p"]')).map(a => ({
                        href: a.href,
                        lines: a.innerText.split('\\n').filter(Boolean)
                    }));
                }""")
                for c in cards_j:
                    lines = c['lines']
                    raw_b = lines[0] if lines[0].lower() in ['samsung', 'lg', 'hisense'] else (lines[1] if len(lines) > 1 and lines[1].lower() in ['samsung', 'lg', 'hisense'] else '')
                    title = " ".join(lines[:2])
                    for l in lines:
                        if 'televisor' in l.lower() or 'smart' in l.lower():
                            title = l
                            break
                    prices = [parse_price(l) for l in lines if '$' in l and not any(w in l.lower() for w in ['cuota', 'mes', 'paga']) and parse_price(l) > 100000]
                    best = min(prices) if prices else 0
                    parsed = parse_brand_item(title, raw_b, best, c['href'], "Jumbo")
                    if parsed:
                        all_items.append(parsed)
            except Exception:
                pass

        browser.close()

    # Deduplicar
    seen = set()
    unique = []
    for it in all_items:
        clean = it['enlace'].split('?')[0].lower()
        if clean and clean not in seen:
            seen.add(clean)
            unique.append(it)

    logging.info(f"Total productos únicos consolidados: {len(unique)}")

    # Estructura separada por marca
    marcas_data = {}
    for b in BRANDS:
        marcas_data[b] = {}
        b_items = [x for x in unique if x['marca'] == b]
        for s in TARGET_SIZES:
            s_matches = [x for x in b_items if x['pulgadas_num'] == s]
            if s_matches:
                s_matches.sort(key=lambda x: x['precio_final'])
                marcas_data[b][str(s)] = s_matches[0]
            else:
                marcas_data[b][str(s)] = None

    # Comparativa lado a lado
    comparativa_marcas = []
    for s in TARGET_SIZES:
        sam = marcas_data['Samsung'].get(str(s))
        lg = marcas_data['LG'].get(str(s))
        his = marcas_data['Hisense'].get(str(s))

        available = [x for x in [sam, lg, his] if x]
        winner = min(available, key=lambda x: x['precio_final']) if available else None

        comparativa_marcas.append({
            "pulgadas": f'{s}"',
            "pulgadas_num": s,
            "ganador": {
                "marca": winner['marca'] if winner else 'N/D',
                "precio_formateado": winner['precio_formateado'] if winner else 'N/D',
                "tienda": winner['tienda'] if winner else 'N/D',
                "enlace": winner['enlace'] if winner else ''
            },
            "samsung": sam,
            "lg": lg,
            "hisense": his
        })

    dataset = {
        "fecha_verificacion": fecha_str,
        "timestamp_iso": ahora.isoformat(),
        "marcas": marcas_data,
        "comparativa_marcas": comparativa_marcas
    }

    print("\n" + "=" * 125)
    print(f"🕒 PRECIOS VERIFICADOS: {fecha_str}")
    print("=" * 125)

    for b in BRANDS:
        print(f"\n📺 TABLA: TELEVISORES MÁS BARATOS DE {b.upper()} POR PULGADAS")
        print("-" * 115)
        print(f"{'Tamaño':<8} | {'Precio Final':<14} | {'Tienda':<10} | {'Tecnología':<25} | {'Título'}")
        print("-" * 115)
        for s in TARGET_SIZES:
            item = marcas_data[b].get(str(s))
            if item:
                trunc = (item['titulo'][:45] + '..') if len(item['titulo']) > 47 else item['titulo']
                print(f"{item['pulgadas']:<8} | {item['precio_formateado']:<14} | {item['tienda']:<10} | {item['tecnologia'][:25]:<25} | {trunc}")
            else:
                print(f"{s}\":{'':<5} | {'Sin inventario':<14} | {'—':<10} | {'—':<25} | —")
        print("-" * 115)

    print("\n" + "=" * 125)
    print("🏆 COMPARATIVA LADO A LADO: SAMSUNG vs LG vs HISENSE")
    print("=" * 125)
    print(f"{'Tamaño':<8} | {'Samsung':<20} | {'LG':<20} | {'Hisense':<20} | {'MARCA GANADORA'}")
    print("-" * 125)
    for row in comparativa_marcas:
        sam_str = f"{row['samsung']['precio_formateado']} ({row['samsung']['tienda']})" if row['samsung'] else "No disponible"
        lg_str = f"{row['lg']['precio_formateado']} ({row['lg']['tienda']})" if row['lg'] else "No disponible"
        his_str = f"{row['hisense']['precio_formateado']} ({row['hisense']['tienda']})" if row['hisense'] else "No disponible"
        win_str = f"🥇 {row['ganador']['marca']} {row['ganador']['precio_formateado']} en {row['ganador']['tienda']}" if row['ganador']['marca'] != 'N/D' else "N/D"
        print(f"{row['pulgadas']:<8} | {sam_str:<20} | {lg_str:<20} | {his_str:<20} | {win_str}")
    print("=" * 125 + "\n")

    json_path = "precios_marcas_separadas.json"
    with open(json_path, 'w', encoding='utf-8') as fp:
        json.dump(dataset, fp, indent=2, ensure_ascii=False)
    logging.info(f"Dataset guardado: {json_path}")

    csv_path = "comparativa_3_marcas.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as fp:
        writer = csv.writer(fp)
        writer.writerow(["Tamaño", "Samsung Precio", "Samsung Tienda", "LG Precio", "LG Tienda", "Hisense Precio", "Hisense Tienda", "Marca Ganadora", "Mejor Precio", "Fecha Verificación"])
        for r in comparativa_marcas:
            writer.writerow([
                r['pulgadas'],
                r['samsung']['precio_formateado'] if r['samsung'] else "N/D",
                r['samsung']['tienda'] if r['samsung'] else "",
                r['lg']['precio_formateado'] if r['lg'] else "N/D",
                r['lg']['tienda'] if r['lg'] else "",
                r['hisense']['precio_formateado'] if r['hisense'] else "N/D",
                r['hisense']['tienda'] if r['hisense'] else "",
                r['ganador']['marca'],
                r['ganador']['precio_formateado'],
                fecha_str
            ])
    logging.info(f"CSV guardado: {csv_path}")

    return dataset

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scraper separado por marcas: Samsung, LG e Hisense.")
    parser.add_argument('--headful', action='store_true', help="Ejecutar con navegador visible.")
    args = parser.parse_args()

    run_scraper(headless=not args.headful)
