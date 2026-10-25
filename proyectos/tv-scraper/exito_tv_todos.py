#!/usr/bin/env python3
"""
Scraper Éxito Colombia - Televisores más baratos para 43, 50, 55, 58, 60 y 65 pulgadas (LG y Samsung).
"""
import sys
import json
import csv
import argparse
from typing import Dict, List
from playwright.sync_api import sync_playwright
from exito_scraper_core import scrape_exito_page, print_result

TARGET_SIZES = [43, 50, 55, 58, 60, 65]

def main():
    parser = argparse.ArgumentParser(description="Obtener los televisores más baratos de Éxito en 43, 50, 55, 58, 60 y 65 pulgadas.")
    parser.add_argument('--headful', action='store_true', help="Ejecutar con navegador visible.")
    args = parser.parse_args()

    print("\n" + "=" * 90)
    print("🚀 EXTRAYENDO TELEVISORES MÁS BARATOS DE ÉXITO (43, 50, 55, 58, 60 y 65 PULGADAS)")
    print("=" * 90)

    # Páginas a consultar en Éxito ordenadas de menor a mayor precio
    urls = []
    # Rangos de la categoría
    for rng in ['40-a-43-pulgadas', '44-a-50-pulgadas', '51-a-60-pulgadas', '61-a-70-pulgadas']:
        urls.append(
            f"https://www.exito.com/tecnologia/televisores"
            f"?category-2=televisores&brand=lg&brand=samsung&rango-tamano-de-pantalla={rng}"
            f"&facets=category-2%2Cbrand%2Crango-tamano-de-pantalla&sort=price_asc&page=0"
        )
    # Búsqueda complementaria para 58 y 60
    urls.append("https://www.exito.com/s?q=televisor+58+pulgadas+samsung&sort=price_asc")
    urls.append("https://www.exito.com/s?q=televisor+60+pulgadas+lg&sort=price_asc")

    all_items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headful,
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

    # Encontrar el más barato para cada tamaño
    results: List[Dict] = []
    for size in TARGET_SIZES:
        matches = [x for x in unique if x['pulgadas_num'] == size]
        if matches:
            matches.sort(key=lambda x: x['precio_final'])
            results.append(matches[0])

    # Imprimir tabla comparativa
    print("\n" + "=" * 110)
    print("📋 RESUMEN: EL TELEVISOR MÁS BARATO DE ÉXITO PARA CADA TAMAÑO SOLICITADO")
    print("=" * 110)
    header = f"{'Tamaño':<8} | {'Marca':<8} | {'Precio Final':<14} | {'Tecnología':<25} | {'Título'}"
    print(header)
    print("-" * 110)

    for tv in results:
        trunc = (tv['titulo'][:45] + '..') if len(tv['titulo']) > 47 else tv['titulo']
        print(f"{tv['pulgadas']:<8} | {tv['marca']:<8} | {tv['precio_formateado']:<14} | {tv['tecnologia'][:25]:<25} | {trunc}")

    print("-" * 110)
    print("\n🔗 ENLACES DIRECTOS A CADA MODELO:\n")
    for tv in results:
        print(f"👉 {tv['pulgadas']} ({tv['marca']} - {tv['precio_formateado']}):")
        print(f"   {tv['enlace']}\n")
    print("=" * 110)

    # Guardar en JSON y CSV
    with open("exito_mas_barato_por_tamano.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open("exito_mas_barato_por_tamano.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=['pulgadas', 'marca', 'precio_final', 'precio_formateado', 'tecnologia', 'titulo', 'enlace'])
        writer.writeheader()
        for tv in results:
            writer.writerow({
                'pulgadas': tv['pulgadas'],
                'marca': tv['marca'],
                'precio_final': tv['precio_final'],
                'precio_formateado': tv['precio_formateado'],
                'tecnologia': tv['tecnologia'],
                'titulo': tv['titulo'],
                'enlace': tv['enlace']
            })

    print("📁 Archivos generados: exito_mas_barato_por_tamano.csv y exito_mas_barato_por_tamano.json\n")

if __name__ == '__main__':
    main()
