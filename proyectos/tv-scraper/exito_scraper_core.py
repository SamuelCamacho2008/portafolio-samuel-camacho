import sys
import re
import json
from typing import Optional, Dict, List
from playwright.sync_api import Page, sync_playwright

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

def parse_tv_item(title: str, raw_brand: str, price_val, url: str) -> Optional[Dict]:
    if not title:
        return None
    title_clean = title.strip()
    title_lower = title_clean.lower()

    # Descartar proyectores o accesorios
    if any(trigger in title_lower for trigger in ['proyector', 'cable hdmi', 'funda protectora']):
        return None
    first_two_words = ' '.join(title_lower.split()[:2])
    if any(trigger in first_two_words for trigger in ['soporte', 'instalación', 'instalacion', 'control', 'cable', 'antena', 'rack']):
        return None
    if not any(term in title_lower for term in ['televisor', 'tv', 'smart']):
        return None

    # Filtrar marcas solicitadas: LG y Samsung
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

    # Tamaño en pulgadas
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
        'tienda': 'Éxito',
        'marca': brand,
        'pulgadas': inches_str,
        'pulgadas_num': inches_num,
        'tecnologia': tech_str,
        'precio_final': price_num,
        'precio_formateado': format_cop(price_num),
        'titulo': title_clean,
        'enlace': url
    }

def scrape_exito_page(page: Page, url: str) -> List[Dict]:
    page.goto(url, wait_until='networkidle', timeout=35000)
    page.wait_for_timeout(2000)
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
    items = []
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
        parsed = parse_tv_item(title, brand, best_price, c['href'])
        if parsed:
            items.append(parsed)
    return items

def get_cheapest_tv_for_size(size: int, headless: bool = True) -> Optional[Dict]:
    """Obtiene el televisor LG o Samsung más barato en Éxito para un tamaño exacto."""
    print(f"\n🔍 Buscando el televisor LG/Samsung más barato de {size}\" en Éxito...")
    
    # URLs para consultar el tamaño
    urls = []
    # 1. Búsqueda directa por tamaño y marcas
    urls.append(f"https://www.exito.com/s?q=televisor+{size}+pulgadas+samsung&sort=price_asc")
    urls.append(f"https://www.exito.com/s?q=televisor+{size}+pulgadas+lg&sort=price_asc")
    
    # 2. Categoría con rango correspondiente
    range_map = {
        43: '40-a-43-pulgadas',
        50: '44-a-50-pulgadas',
        55: '51-a-60-pulgadas',
        58: '51-a-60-pulgadas',
        60: '51-a-60-pulgadas',
        65: '61-a-70-pulgadas'
    }
    rng = range_map.get(size)
    if rng:
        urls.append(
            f"https://www.exito.com/tecnologia/televisores"
            f"?category-2=televisores&brand=lg&brand=samsung&rango-tamano-de-pantalla={rng}"
            f"&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0"
        )
        urls.append(
            f"https://www.exito.com/tecnologia/televisores"
            f"?category-2=televisores&brand=lg&brand=samsung&rango-tamano-de-pantalla={rng}"
            f"&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=1"
        )

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

        for u in urls:
            try:
                scraped = scrape_exito_page(page, u)
                all_items.extend(scraped)
            except Exception as e:
                pass

        browser.close()

    # Deduplicar
    unique = []
    seen = set()
    for it in all_items:
        clean = it['enlace'].split('?')[0].lower()
        if clean and clean not in seen:
            seen.add(clean)
            unique.append(it)

    # Filtrar tamaño exacto
    matches = [x for x in unique if x['pulgadas_num'] == size]
    if not matches:
        return None

    matches.sort(key=lambda x: x['precio_final'])
    return matches[0]

def print_result(tv: Dict):
    print("\n" + "=" * 80)
    print(f"🏆 TELEVISOR MÁS BARATO DE {tv['pulgadas']} EN ÉXITO COLOMBIA")
    print("=" * 80)
    print(f" Marca:      {tv['marca']}")
    print(f" Tamaño:     {tv['pulgadas']}")
    print(f" Precio:     {tv['precio_formateado']} COP")
    print(f" Tecnología: {tv['tecnologia']}")
    print(f" Título:     {tv['titulo']}")
    print(f" Enlace:     {tv['enlace']}")
    print("=" * 80 + "\n")
