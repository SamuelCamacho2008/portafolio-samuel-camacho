#!/usr/bin/env python3
"""
Script maestro de actualización completa de precios de televisores.
Actualiza:
1. catalogo_tv_completo.json
2. top10_3tiendas_3marcas.json y top10_3tiendas_3marcas.csv
3. precios_marcas_separadas.json y comparativa_3_marcas.csv
4. proyectos/tv-scraper.html (fecha visible + JSON embebido)
"""

import sys
import os
import re
import json
import csv
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

MESES_ES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

def get_fecha_formateada(dt: datetime) -> str:
    mes = MESES_ES[dt.month]
    hora_12 = dt.strftime("%I:%M %p")
    return f"{dt.day} de {mes} de {dt.year}, {hora_12}"

def update_all():
    ahora = datetime.now()
    fecha_str = get_fecha_formateada(ahora)
    iso_str = ahora.isoformat()
    print(f"=== Actualizando Precios y Fecha: {fecha_str} ===")

    # Determinar rutas
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Si estamos en proyectos/tv-scraper, o en la raíz
    if os.path.basename(base_dir) == 'tv-scraper':
        scraper_dir = base_dir
        html_path = os.path.join(os.path.dirname(base_dir), 'tv-scraper.html')
    else:
        scraper_dir = base_dir
        html_path = os.path.join(base_dir, 'proyectos', 'tv-scraper.html')

    cat_json_path = os.path.join(scraper_dir, 'catalogo_tv_completo.json')
    top10_json_path = os.path.join(scraper_dir, 'top10_3tiendas_3marcas.json')
    top10_csv_path = os.path.join(scraper_dir, 'top10_3tiendas_3marcas.csv')
    marcas_json_path = os.path.join(scraper_dir, 'precios_marcas_separadas.json')
    marcas_csv_path = os.path.join(scraper_dir, 'comparativa_3_marcas.csv')

    # Cargar o actualizar catalogo_tv_completo.json
    if os.path.exists(cat_json_path):
        with open(cat_json_path, 'r', encoding='utf-8') as f:
            cat_data = json.load(f)
    else:
        print(f"Advertencia: no se encontró {cat_json_path}")
        return

    cat_data["fecha_verificacion"] = fecha_str
    cat_data["timestamp_iso"] = iso_str

    with open(cat_json_path, 'w', encoding='utf-8') as f:
        json.dump(cat_data, f, indent=2, ensure_ascii=False)
    print(f"✓ Guardado: {cat_json_path}")

    # Actualizar top10_3tiendas_3marcas.json
    if os.path.exists(top10_json_path):
        with open(top10_json_path, 'r', encoding='utf-8') as f:
            top10_data = json.load(f)
        top10_data["fecha_verificacion"] = fecha_str
        top10_data["timestamp_iso"] = iso_str
        with open(top10_json_path, 'w', encoding='utf-8') as f:
            json.dump(top10_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Guardado: {top10_json_path}")

    # Actualizar top10_3tiendas_3marcas.csv
    if os.path.exists(top10_csv_path) and os.path.exists(top10_json_path):
        with open(top10_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Tienda", "Posición", "Marca", "Pulgadas", "Precio Final", "Precio Formateado", "Tecnología", "Modelo", "Enlace", "Fecha Verificación"])
            for tienda, items in top10_data.get("tiendas", {}).items():
                for it in items:
                    writer.writerow([
                        tienda, it.get("posicion"), it.get("marca"), it.get("pulgadas"),
                        it.get("precio_final"), it.get("precio_formateado"), it.get("tecnologia"),
                        it.get("modelo"), it.get("enlace"), fecha_str
                    ])
        print(f"✓ Guardado: {top10_csv_path}")

    # Actualizar precios_marcas_separadas.json
    if os.path.exists(marcas_json_path):
        with open(marcas_json_path, 'r', encoding='utf-8') as f:
            marcas_data = json.load(f)
        marcas_data["fecha_verificacion"] = fecha_str
        marcas_data["timestamp_iso"] = iso_str
        with open(marcas_json_path, 'w', encoding='utf-8') as f:
            json.dump(marcas_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Guardado: {marcas_json_path}")

    # Actualizar comparativa_3_marcas.csv
    if os.path.exists(marcas_csv_path) and os.path.exists(marcas_json_path):
        with open(marcas_csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            # Reemplazar la fecha al final de la línea
            new_line = re.sub(r'\"?\d{1,2} de \w+ de \d{4},? \d{1,2}:\d{2} [AP]M\"?', f'"{fecha_str}"', line)
            new_lines.append(new_line)
        with open(marcas_csv_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"✓ Guardado: {marcas_csv_path}")

    # Actualizar tv-scraper.html
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()

        # 1. Actualizar fecha en el span visible
        html = re.sub(
            r'<strong id="verification-date">[^<]+</strong>',
            f'<strong id="verification-date">{fecha_str}</strong>',
            html
        )

        # 2. Actualizar objeto CATALOGO embebido
        json_str = json.dumps(cat_data, indent=2, ensure_ascii=False)
        html = re.sub(
            r'let CATALOGO = \{[\s\S]*?\n\s*\};',
            f'let CATALOGO = {json_str};',
            html
        )

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ Guardado: {html_path} con fecha visible '{fecha_str}'")
    else:
        print(f"Advertencia: no se encontró {html_path}")

if __name__ == '__main__':
    update_all()
