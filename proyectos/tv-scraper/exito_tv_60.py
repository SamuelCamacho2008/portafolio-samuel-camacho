#!/usr/bin/env python3
"""
Scraper Éxito Colombia - Televisor más barato de 60 pulgadas (LG / Samsung).
"""
import sys
import argparse
from exito_scraper_core import get_cheapest_tv_for_size, print_result

SIZE = 60

def main():
    parser = argparse.ArgumentParser(description=f"Televisor más barato de {SIZE} pulgadas en Éxito.")
    parser.add_argument('--headful', action='store_true', help="Ejecutar con navegador visible.")
    args = parser.parse_args()

    tv = get_cheapest_tv_for_size(SIZE, headless=not args.headful)
    if tv:
        print_result(tv)
    else:
        print(f"❌ No se encontró ningún televisor LG o Samsung de {SIZE}\" en Éxito.")

if __name__ == '__main__':
    main()
