#!/usr/bin/env python3
"""
Scraper de Televisores LG y Samsung en Éxito y Falabella Colombia
Ordenados de menor a mayor precio con Playwright.
Soporta filtrado por tamaño mínimo en pulgadas (ej. 50" en adelante).
"""

import sys
import os
import re
import json
import csv
import argparse
import logging
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright

# Configurar salida UTF-8 para consola de Windows
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


def parse_price(val) -> int:
    """Limpia y convierte cualquier representación de precio a un entero en pesos colombianos."""
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        cleaned = re.sub(r'[^\d]', '', val)
        if cleaned:
            return int(cleaned)
    return 0


def format_cop(val: int) -> str:
    """Formatea un número entero a formato de moneda colombiana ($ 1.234.567)."""
    return f"${val:,.0f}".replace(',', '.')


def parse_tv_item(title: str, raw_brand: str, price_val, url: str, store: str) -> Optional[Dict]:
    """
    Normaliza y extrae los campos requeridos:
    - Marca (LG o Samsung)
    - Tamaño en pulgadas (numérico y formateado)
    - Tecnología (LED, 4K, Smart TV, OLED, QLED, etc.)
    - Precio final
    - Enlace
    - Tienda
    """
    if not title:
        return None
    title_clean = title.strip()
    title_lower = title_clean.lower()

    # 1. Descartar accesorios, proyectores o servicios
    exclude_triggers = ['soporte', 'instalación', 'instalacion', 'control remoto', 'cable', 'funda', 'antena', 'rack', 'proyector']
    if any(trigger in title_lower for trigger in ['proyector', 'cable hdmi', 'funda protectora']):
        return None
    first_two_words = ' '.join(title_lower.split()[:2])
    if any(trigger in first_two_words for trigger in ['soporte', 'instalación', 'instalacion', 'control', 'cable', 'antena', 'rack']):
        return None

    # Debe ser televisor o pantalla de TV
    if not any(term in title_lower for term in ['televisor', 'tv', 'smart']):
        return None

    # 2. Filtrar únicamente marcas solicitadas: LG y Samsung
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

    # 3. Tamaño en pulgadas
    m_inch = re.search(r'(\d{2,3})\s*(?:\"|”|″|\'\'|\b(?:pulgadas?|pulg|in)\b)', title_clean, re.IGNORECASE)
    inches_num = None
    if m_inch:
        inches_num = int(m_inch.group(1))
        inches_str = f'{inches_num}"'
    else:
        # Extraer del código de modelo (ej: UN32..., 43CU..., 50M..., 55QN...)
        m_model = re.search(r'\b(?:UN|QN|QNED|OLED|UR|UT|DU|CU|AU|MRN)?(\d{2})[A-Z0-9]', title_clean)
        common_sizes = [24, 28, 32, 40, 42, 43, 48, 50, 55, 58, 60, 65, 70, 75, 77, 83, 85, 86, 98]
        if m_model and int(m_model.group(1)) in common_sizes:
            inches_num = int(m_model.group(1))
            inches_str = f'{inches_num}"'
        else:
            inches_str = 'N/D'

    # 4. Tecnologías (LED, 4K, Smart TV, OLED, QLED, etc.)
    techs = []
    # Panel
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

    # Resolución
    if re.search(r'\b(4k|uhd|uhd4k|ultra\s*hd)\b', title_lower):
        techs.append('4K UHD')
    elif re.search(r'\b(full\s*hd|fhd|1080p)\b', title_lower):
        techs.append('Full HD')
    elif re.search(r'\bhd\b', title_lower):
        techs.append('HD')

    # Smart TV
    if re.search(r'\bsmart\s*tv\b|\bsmarttv\b|\bsmart\b', title_lower):
        techs.append('Smart TV')

    # Sistema operativo / características
    if 'tizen' in title_lower:
        techs.append('Tizen OS')
    if 'webos' in title_lower:
        techs.append('webOS')

    if not techs:
        techs.append('Smart TV')

    tech_str = ', '.join(dict.fromkeys(techs))

    # 5. Precio
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


def scrape_falabella(page, min_inches: Optional[int] = None) -> List[Dict]:
    """
    Extrae televisores de Falabella Colombia ordenados de menor a mayor precio.
    Si se especifica min_inches, consulta las búsquedas correspondientes a esos tamaños.
    """
    items = []
    urls = []

    if min_inches and min_inches >= 50:
        # Consultar tamaños principales de 50 en adelante
        sizes = [50, 55, 58, 65, 70, 75]
        for s in sizes:
            urls.append(
                f"https://www.falabella.com.co/falabella-co/search"
                f"?Ntt=televisor+{s}+pulgadas&f.product.brandName=samsung%3A%3Alg&sortBy=derived.price.search%2Casc"
            )
    else:
        urls.append(
            "https://www.falabella.com.co/falabella-co/search"
            "?Ntt=televisores&f.product.brandName=samsung%3A%3Alg&sortBy=derived.price.search%2Casc"
        )

    for target_url in urls:
        logging.info(f"[Falabella] Consultando: {target_url}")
        try:
            page.goto(target_url, wait_until='networkidle', timeout=40000)
            raw_next_data = page.locator('#__NEXT_DATA__').inner_text()
            next_data = json.loads(raw_next_data)
            results = next_data.get('props', {}).get('pageProps', {}).get('results', [])

            for r in results:
                title = r.get('displayName')
                brand = r.get('brandName') or r.get('brand')
                prod_url = r.get('url') or ''
                if prod_url and not prod_url.startswith('http'):
                    prod_url = f"https://www.falabella.com.co{prod_url}"

                prices = r.get('prices', [])
                active_prices = []
                for p in prices:
                    if not p.get('crossed', False):
                        p_val_list = p.get('price', [])
                        if p_val_list:
                            num = parse_price(p_val_list[0])
                            if num > 0:
                                active_prices.append(num)

                best_price = min(active_prices) if active_prices else 0
                parsed = parse_tv_item(title, brand, best_price, prod_url, "Falabella")
                if parsed:
                    if min_inches is None or (parsed['pulgadas_num'] and parsed['pulgadas_num'] >= min_inches):
                        items.append(parsed)
        except Exception as e:
            logging.error(f"[Falabella] Error procesando URL: {e}")

    logging.info(f"[Falabella] {len(items)} televisores procesados")
    return items


def scrape_exito(page, min_inches: Optional[int] = None) -> List[Dict]:
    """
    Extrae televisores de Éxito Colombia ordenados de menor a mayor precio.
    Si se especifica min_inches >= 50, consulta los rangos de pantalla correspondientes.
    """
    items = []
    urls = []

    if min_inches and min_inches >= 50:
        ranges = ['44-a-50-pulgadas', '51-a-60-pulgadas', '61-a-70-pulgadas', '71-pulgadas-o-mas']
        for r in ranges:
            urls.append(
                f"https://www.exito.com/tecnologia/televisores"
                f"?category-2=televisores&brand=lg&brand=samsung&rango-tamano-de-pantalla={r}"
                f"&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0"
            )
    else:
        urls.append(
            "https://www.exito.com/tecnologia/televisores"
            "?category-2=televisores&brand=lg&category-1=tecnologia&brand=samsung"
            "&category-1=tecnologia&facets=category-2%2Cbrand%2Ccategory-1&sort=price_asc&page=0"
        )

    for target_url in urls:
        logging.info(f"[Éxito] Consultando: {target_url}")
        try:
            page.goto(target_url, wait_until='networkidle', timeout=40000)
            page.wait_for_timeout(2500)

            cards_data = page.evaluate("""() => {
                const articles = Array.from(document.querySelectorAll('article'));
                return articles.map(a => {
                    const link = a.querySelector('a');
                    const href = link ? link.href : '';
                    
                    const titleEl = a.querySelector('h3, [class*="productCard_productCard__name"], a[title]');
                    const title = titleEl ? (titleEl.innerText || titleEl.getAttribute('title') || '') : '';

                    const brandEl = a.querySelector('[class*="productCard_productCard__brand"], [data-fs-product-card-brand]');
                    const brand = brandEl ? brandEl.innerText : '';

                    const priceEls = Array.from(a.querySelectorAll('[data-fs-price="true"], [class*="ProductPrice_container__price"], [class*="price_fs-price"]'));
                    const prices = priceEls.map(p => p.innerText.trim()).filter(Boolean);

                    const allText = a.innerText.split('\\n').map(t => t.trim()).filter(Boolean);

                    return { title, brand, prices, allText, href };
                });
            }""")

            for c in cards_data:
                title = c['title']
                brand = c['brand']
                all_text = c['allText']

                if not title or 'patrocinado' in title.lower():
                    for line in all_text:
                        if 'televisor' in line.lower() or 'tv' in line.lower():
                            title = line
                            break

                found_prices = []
                for p_str in c['prices']:
                    p_val = parse_price(p_str)
                    if p_val > 100000:
                        found_prices.append(p_val)

                if not found_prices:
                    for line in all_text:
                        if '$' in line and not any(w in line.lower() for w in ['cuota', 'mes', 'seguro']):
                            p_val = parse_price(line)
                            if p_val > 100000:
                                found_prices.append(p_val)

                best_price = min(found_prices) if found_prices else 0
                parsed = parse_tv_item(title, brand, best_price, c['href'], "Éxito")
                if parsed:
                    if min_inches is None or (parsed['pulgadas_num'] and parsed['pulgadas_num'] >= min_inches):
                        items.append(parsed)
        except Exception as e:
            logging.error(f"[Éxito] Error procesando URL: {e}")

    logging.info(f"[Éxito] {len(items)} televisores procesados")
    return items


def save_results(items: List[Dict], output_json: str, output_csv: str):
    """Guarda los resultados del Top 10 en formatos JSON y CSV."""
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    logging.info(f"Top 10 guardado en JSON: {output_json}")

    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['puesto', 'tienda', 'marca', 'pulgadas', 'tecnologia', 'precio_final', 'precio_formateado', 'titulo', 'enlace']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, item in enumerate(items, 1):
            row = {
                'puesto': idx,
                'tienda': item['tienda'],
                'marca': item['marca'],
                'pulgadas': item['pulgadas'],
                'tecnologia': item['tecnologia'],
                'precio_final': item['precio_final'],
                'precio_formateado': item['precio_formateado'],
                'titulo': item['titulo'],
                'enlace': item['enlace']
            }
            writer.writerow(row)
    logging.info(f"Top 10 guardado en CSV: {output_csv}")


def print_top_table(items: List[Dict], min_inches: Optional[int] = None):
    """Imprime el Top 10 en formato tabla estructurada en la terminal."""
    size_label = f"({min_inches}\" EN ADELANTE)" if min_inches else ""
    print("\n" + "=" * 115)
    print(f"🏆 TOP 10 TELEVISORES MÁS BARATOS {size_label} (LG & SAMSUNG) - ÉXITO Y FALABELLA")
    print("=" * 115)
    header = f"{'#':<3} | {'Tienda':<10} | {'Marca':<8} | {'Tamaño':<7} | {'Precio':<12} | {'Tecnología':<22} | {'Título'}"
    print(header)
    print("-" * 115)

    for idx, tv in enumerate(items, 1):
        trunc_title = (tv['titulo'][:38] + '..') if len(tv['titulo']) > 40 else tv['titulo']
        row = (
            f"{idx:<3} | "
            f"{tv['tienda']:<10} | "
            f"{tv['marca']:<8} | "
            f"{tv['pulgadas']:<7} | "
            f"{tv['precio_formateado']:<12} | "
            f"{tv['tecnologia'][:22]:<22} | "
            f"{trunc_title}"
        )
        print(row)

    print("-" * 115)
    print("\n🔗 ENLACES DIRECTOS A LOS PRODUCTOS DEL TOP 10:\n")
    for idx, tv in enumerate(items, 1):
        print(f"[{idx}] {tv['marca']} {tv['pulgadas']} ({tv['tienda']} - {tv['precio_formateado']}):")
        print(f"    {tv['enlace']}\n")
    print("=" * 115)


def run_scraper(min_inches: Optional[int] = None, headless: bool = True):
    """Ejecuta el flujo completo de Playwright para Éxito y Falabella."""
    logging.info(f"Iniciando Playwright Chromium... (Filtro mínimo de pulgadas: {min_inches or 'Todos'})")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-infobars'
            ]
        )
        context = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            )
        )
        page = context.new_page()

        # 1. Extraer Falabella
        falabella_items = scrape_falabella(page, min_inches=min_inches)

        # 2. Extraer Éxito
        exito_items = scrape_exito(page, min_inches=min_inches)

        browser.close()

    # Combinar resultados
    all_items = falabella_items + exito_items

    # Deduplicar por enlace base (sin query params)
    seen_urls = set()
    unique_items = []
    for item in all_items:
        clean_url = item['enlace'].split('?')[0].lower()
        if clean_url and clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)
        unique_items.append(item)

    # Filtrar por pulgadas mínimas si aplica
    if min_inches:
        unique_items = [x for x in unique_items if x['pulgadas_num'] and x['pulgadas_num'] >= min_inches]

    # Ordenar estrictamente de menor a mayor precio
    unique_items.sort(key=lambda x: x['precio_final'])

    # Extraer Top 10
    top_10 = unique_items[:10]

    # Imprimir
    print_top_table(top_10, min_inches=min_inches)

    # Archivos de salida
    json_name = f"top10_televisores_{min_inches}pulg.json" if min_inches else "top10_televisores.json"
    csv_name = f"top10_televisores_{min_inches}pulg.csv" if min_inches else "top10_televisores.csv"
    save_results(top_10, json_name, csv_name)

    return top_10


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scraper de televisores LG y Samsung en Éxito y Falabella Colombia.")
    parser.add_argument('--min-inches', type=int, default=None, help="Filtrar por tamaño mínimo en pulgadas (ej. 50).")
    parser.add_argument('--headful', action='store_true', help="Ejecutar con navegador visible (por defecto es headless).")
    args = parser.parse_args()

    run_scraper(min_inches=args.min_inches, headless=not args.headful)
