#!/usr/bin/env python3
"""
Scraper Multi-Retail Colombia: Éxito, Falabella y Jumbo
Extrae el televisor LG o Samsung más barato por tamaño (43", 50", 55", 58", 60" y 65").
Genera un dataset consolidado con fecha y hora de verificación de precios.
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

def parse_tv_item(title: str, raw_brand: str, price_val, url: str, store: str) -> Optional[Dict]:
    if not title:
        return None
    title_clean = title.strip()
    title_lower = title_clean.lower()

    # Descartar proyectores, soportes, cables
    if any(trigger in title_lower for trigger in ['proyector', 'cable hdmi', 'funda protectora']):
        return None
    first_two_words = ' '.join(title_lower.split()[:2])
    if any(trigger in first_two_words for trigger in ['soporte', 'instalación', 'instalacion', 'control', 'cable', 'antena', 'rack']):
        return None
    if not any(term in title_lower for term in ['televisor', 'tv', 'smart']):
        return None

    # Marcas: LG o Samsung
    brand = None
    if raw_brand and 'samsung' in raw_brand.lower():
        brand = 'Samsung'
    elif raw_brand and 'lg' in raw_brand.lower():
        brand = 'LG'
    elif 'samsung' in title_lower:
        brand = 'Samsung'
    elif re.search(r'\blg\b', title_lower):
        brand = 'LG'

    if not brand:
        return None

    # Pulgadas
    m_inch = re.search(r'(\d{2,3})\s*(?:\"|”|″|\'\'|\b(?:pulgadas?|pulg|in)\b)', title_clean, re.IGNORECASE)
    inches_num = None
    if m_inch:
        inches_num = int(m_inch.group(1))
        inches_str = f'{inches_num}"'
    else:
        m_model = re.search(r'\b(?:UN|QN|QNED|OLED|UR|UT|DU|CU|AU|MRN)?(\d{2})[A-Z0-9]', title_clean)
        common_sizes = [24, 28, 32, 40, 42, 43, 48, 50, 55, 58, 60, 65, 70, 75, 77, 83, 85, 86, 98]
        if m_model and int(m_model.group(1)) in common_sizes:
            inches_num = int(m_model.group(1))
            inches_str = f'{inches_num}"'
        else:
            inches_str = 'N/D'

    # Tecnologías
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

    if re.search(r'\bsmart\s*tv\b|\bsmarttv\b|\bsmart\b', title_lower):
        techs.append('Smart TV')
    if 'tizen' in title_lower:
        techs.append('Tizen OS')
    if 'webos' in title_lower:
        techs.append('webOS')

    if not techs:
        techs.append('Smart TV')

    tech_str = ', '.join(dict.fromkeys(techs))
    price_num = parse_price(price_val)
    if price_num < 100000:
        return None

    return {
        'tienda': store,
        'marca': brand,
        'pulgadas': inches_str,
        'pulgadas_num': inches_num,
        'tecnologia': tech_str,
        'precio_final': price_num,
        'precio_formateado': format_cop(price_num),
        'titulo': title_clean,
        'enlace': url
    }

# --- 1. EXITO ---
def scrape_exito_sizes(page) -> Dict[int, Dict]:
    logging.info("[Éxito] Iniciando extracción por tamaños...")
    urls = [
        "https://www.exito.com/tecnologia/televisores?category-2=televisores&brand=lg&brand=samsung&rango-tamano-de-pantalla=40-a-43-pulgadas&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0",
        "https://www.exito.com/tecnologia/televisores?category-2=televisores&brand=lg&brand=samsung&rango-tamano-de-pantalla=44-a-50-pulgadas&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0",
        "https://www.exito.com/tecnologia/televisores?category-2=televisores&brand=lg&brand=samsung&rango-tamano-de-pantalla=51-a-60-pulgadas&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0",
        "https://www.exito.com/tecnologia/televisores?category-2=televisores&brand=lg&brand=samsung&rango-tamano-de-pantalla=61-a-70-pulgadas&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0",
        "https://www.exito.com/s?q=televisor+58+pulgadas+samsung&sort=price_asc",
        "https://www.exito.com/s?q=televisor+60+pulgadas+lg&sort=price_asc"
    ]
    items = []
    for u in urls:
        try:
            page.goto(u, wait_until='networkidle', timeout=30000)
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
                brand = c['brand']
                all_text = c['allText']
                if not title or 'patrocinado' in title.lower():
                    for line in all_text:
                        if 'televisor' in line.lower() or 'tv' in line.lower():
                            title = line
                            break
                found_prices = [parse_price(p) for p in c['prices'] if parse_price(p) > 100000]
                if not found_prices:
                    for line in all_text:
                        if '$' in line and not any(w in line.lower() for w in ['cuota', 'mes', 'seguro']):
                            val = parse_price(line)
                            if val > 100000:
                                found_prices.append(val)
                best_price = min(found_prices) if found_prices else 0
                parsed = parse_tv_item(title, brand, best_price, c['href'], "Éxito")
                if parsed:
                    items.append(parsed)
        except Exception:
            pass

    by_size = {}
    for s in TARGET_SIZES:
        m = [x for x in items if x['pulgadas_num'] == s]
        if m:
            m.sort(key=lambda x: x['precio_final'])
            by_size[s] = m[0]
    logging.info(f"[Éxito] Encontrados modelos para {len(by_size)}/{len(TARGET_SIZES)} tamaños")
    return by_size

# --- 2. FALABELLA ---
def scrape_falabella_sizes(page) -> Dict[int, Dict]:
    logging.info("[Falabella] Iniciando extracción por tamaños...")
    items = []
    for s in TARGET_SIZES:
        url = f"https://www.falabella.com.co/falabella-co/search?Ntt=televisor+{s}+pulgadas&f.product.brandName=samsung%3A%3Alg&sortBy=derived.price.search%2Casc"
        try:
            page.goto(url, wait_until='networkidle', timeout=30000)
            raw = page.locator('#__NEXT_DATA__').inner_text()
            d = json.loads(raw)
            results = d.get('props', {}).get('pageProps', {}).get('results', [])
            for r in results:
                title = r.get('displayName')
                brand = r.get('brandName') or r.get('brand')
                prod_url = r.get('url') or ''
                if prod_url and not prod_url.startswith('http'):
                    prod_url = f"https://www.falabella.com.co{prod_url}"
                prices = r.get('prices', [])
                active = []
                for p in prices:
                    if not p.get('crossed', False):
                        p_val = p.get('price', [])
                        if p_val:
                            num = parse_price(p_val[0])
                            if num > 0:
                                active.append(num)
                best_price = min(active) if active else 0
                parsed = parse_tv_item(title, brand, best_price, prod_url, "Falabella")
                if parsed:
                    items.append(parsed)
        except Exception:
            pass

    by_size = {}
    for s in TARGET_SIZES:
        m = [x for x in items if x['pulgadas_num'] == s]
        if m:
            m.sort(key=lambda x: x['precio_final'])
            by_size[s] = m[0]
    logging.info(f"[Falabella] Encontrados modelos para {len(by_size)}/{len(TARGET_SIZES)} tamaños")
    return by_size

# --- 3. JUMBO ---
def scrape_jumbo_sizes(page) -> Dict[int, Dict]:
    logging.info("[Jumbo] Iniciando extracción por tamaños...")
    urls = [
        "https://www.jumbocolombia.com/co/televisores-y-audio/television/samsung?order=OrderByPriceASC",
        "https://www.jumbocolombia.com/co/televisores-y-audio/television/lg?order=OrderByPriceASC"
    ]
    items = []
    for u in urls:
        try:
            page.goto(u, wait_until='domcontentloaded', timeout=25000)
            page.wait_for_timeout(3500)
            cards = page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a[href*="/p"]'));
                return links.map(a => ({
                    href: a.href,
                    lines: a.innerText.split('\\n').filter(Boolean)
                }));
            }""")
            for c in cards:
                lines = c['lines']
                if len(lines) < 2:
                    continue
                brand = lines[0] if lines[0].lower() in ['samsung', 'lg'] else (lines[1] if len(lines) > 1 and lines[1].lower() in ['samsung', 'lg'] else '')
                title = ""
                for l in lines:
                    if 'televisor' in l.lower() or 'smart tv' in l.lower():
                        title = l
                        break
                if not title:
                    title = lines[1] if len(lines) > 1 else lines[0]

                prices = []
                for l in lines:
                    if '$' in l and not any(w in l.lower() for w in ['cuota', 'mes', 'paga']):
                        val = parse_price(l)
                        if val > 100000:
                            prices.append(val)
                if not prices:
                    for l in lines:
                        if '$' in l and not any(w in l.lower() for w in ['cuota', 'mes']):
                            val = parse_price(l)
                            if val > 100000:
                                prices.append(val)

                best_price = min(prices) if prices else 0
                parsed = parse_tv_item(title, brand, best_price, c['href'], "Jumbo")
                if parsed:
                    items.append(parsed)
        except Exception:
            pass

    by_size = {}
    for s in TARGET_SIZES:
        m = [x for x in items if x['pulgadas_num'] == s]
        if m:
            m.sort(key=lambda x: x['precio_final'])
            by_size[s] = m[0]
    logging.info(f"[Jumbo] Encontrados modelos para {len(by_size)}/{len(TARGET_SIZES)} tamaños")
    return by_size

def run_multiretail_scraper(headless: bool = True):
    ahora = datetime.now()
    fecha_str = get_fecha_formateada(ahora)
    logging.info(f"Fecha de verificación asignada: {fecha_str}")

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

        exito_data = scrape_exito_sizes(page)
        falabella_data = scrape_falabella_sizes(page)
        jumbo_data = scrape_jumbo_sizes(page)

        browser.close()

    # Formar estructura consolidada
    data_out = {
        "fecha_verificacion": fecha_str,
        "timestamp_iso": ahora.isoformat(),
        "tiendas": {
            "exito": {str(s): exito_data.get(s) for s in TARGET_SIZES},
            "falabella": {str(s): falabella_data.get(s) for s in TARGET_SIZES},
            "jumbo": {str(s): jumbo_data.get(s) for s in TARGET_SIZES}
        },
        "comparativa_global": []
    }

    # Armar comparativa lado a lado
    for s in TARGET_SIZES:
        e = exito_data.get(s)
        f = falabella_data.get(s)
        j = jumbo_data.get(s)

        # Encontrar cuál tienda es la ganadora en precio
        available = [x for x in [e, f, j] if x]
        winner = min(available, key=lambda x: x['precio_final']) if available else None

        data_out["comparativa_global"].append({
            "pulgadas": f'{s}"',
            "pulgadas_num": s,
            "ganador": {
                "tienda": winner['tienda'] if winner else 'N/D',
                "precio": winner['precio_final'] if winner else None,
                "precio_formateado": winner['precio_formateado'] if winner else 'N/D',
                "marca": winner['marca'] if winner else 'N/D',
                "enlace": winner['enlace'] if winner else ''
            },
            "exito": e,
            "falabella": f,
            "jumbo": j
        })

    # Imprimir en consola la tabla comparativa
    print("\n" + "=" * 125)
    print(f"🏆 COMPARATIVA 3 TIENDAS (ÉXITO vs FALABELLA vs JUMBO) — LG & SAMSUNG")
    print(f"🕒 Precios verificados: {fecha_str}")
    print("=" * 125)
    print(f"{'Tamaño':<8} | {'Éxito':<18} | {'Falabella':<18} | {'Jumbo':<18} | {'MEJOR OFERTA (GANADOR)'}")
    print("-" * 125)

    for row in data_out["comparativa_global"]:
        e_str = f"{row['exito']['marca']} {row['exito']['precio_formateado']}" if row['exito'] else "No disponible"
        f_str = f"{row['falabella']['marca']} {row['falabella']['precio_formateado']}" if row['falabella'] else "No disponible"
        j_str = f"{row['jumbo']['marca']} {row['jumbo']['precio_formateado']}" if row['jumbo'] else "No disponible"
        win_str = f"🥇 {row['ganador']['tienda']} ({row['ganador']['marca']} {row['ganador']['precio_formateado']})" if row['ganador']['precio'] else "N/D"

        print(f"{row['pulgadas']:<8} | {e_str:<18} | {f_str:<18} | {j_str:<18} | {win_str}")

    print("=" * 125 + "\n")

    # Guardar en JSON en el workspace actual
    json_path = "precios_retail_verificados.json"
    with open(json_path, 'w', encoding='utf-8') as fp:
        json.dump(data_out, fp, indent=2, ensure_ascii=False)
    logging.info(f"Dataset guardado: {json_path}")

    # Guardar CSV comparativo
    csv_path = "comparativa_3_tiendas.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as fp:
        writer = csv.writer(fp)
        writer.writerow(["Tamaño", "Éxito Marca", "Éxito Precio", "Falabella Marca", "Falabella Precio", "Jumbo Marca", "Jumbo Precio", "Tienda Ganadora", "Mejor Precio", "Fecha Verificación"])
        for row in data_out["comparativa_global"]:
            writer.writerow([
                row['pulgadas'],
                row['exito']['marca'] if row['exito'] else "",
                row['exito']['precio_formateado'] if row['exito'] else "N/D",
                row['falabella']['marca'] if row['falabella'] else "",
                row['falabella']['precio_formateado'] if row['falabella'] else "N/D",
                row['jumbo']['marca'] if row['jumbo'] else "",
                row['jumbo']['precio_formateado'] if row['jumbo'] else "N/D",
                row['ganador']['tienda'],
                row['ganador']['precio_formateado'],
                fecha_str
            ])
    logging.info(f"CSV guardado: {csv_path}")

    return data_out

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scraper multi-retail Éxito, Falabella y Jumbo.")
    parser.add_argument('--headful', action='store_true', help="Ejecutar con navegador visible.")
    args = parser.parse_args()

    run_multiretail_scraper(headless=not args.headful)
