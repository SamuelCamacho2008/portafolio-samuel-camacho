# Playwright Retail Scraper — Éxito & Falabella Colombia 📺

Extractor automatizado y comparador de precios en tiempo real para las categorías de tecnología y televisores en **Éxito** y **Falabella Colombia**, enfocado en marcas líderes (**LG y Samsung**).

---

## 🚀 Características

- **Automatización Headless con Playwright:** Navegación en SPAs complejas basadas en VTEX FastStore (Éxito) y Next.js (Falabella).
- **Extracción Híbrida Inteligente:** Combina parsing de datos embebidos (`__NEXT_DATA__`) con selectores DOM adaptativos para lidiar con hidratación reactiva y lazy-loading.
- **Normalización Técnica de Datos:**
  - Tamaño en pulgadas (`32"`, `43"`, `50"`, `55"`, `58"`, `60"`, `65"`, etc.).
  - Panel y tecnologías (`OLED`, `QNED`, `Neo QLED`, `Crystal UHD`, `Mini LED`, `LED`).
  - Resolución (`4K UHD`, `Full HD`, `HD`).
  - Ecosistema Smart TV (`Tizen OS`, `webOS`, etc.).
  - Filtro estricto contra accesorios (exclusión de soportes, cables HDMI, controles o proyectores).
- **Salidas Estructuradas:** Consola interactiva en formato tabla, exportación a **CSV** y **JSON**.

---

## 📁 Estructura de Scripts

| Script | Descripción |
|---|---|
| `scraper_tv.py` | Scraper completo multi-tienda (Éxito + Falabella). Soporta `--min-inches 50` y `--headful`. |
| `exito_scraper_core.py` | Motor centralizado de scraping, filtrado y parsing para Éxito Colombia. |
| `exito_tv_43.py` | Extrae el televisor más barato de **43 pulgadas** en Éxito. |
| `exito_tv_50.py` | Extrae el televisor más barato de **50 pulgadas** en Éxito. |
| `exito_tv_55.py` | Extrae el televisor más barato de **55 pulgadas** en Éxito. |
| `exito_tv_58.py` | Extrae el televisor más barato de **58 pulgadas** en Éxito. |
| `exito_tv_60.py` | Extrae el televisor más barato de **60 pulgadas** en Éxito. |
| `exito_tv_65.py` | Extrae el televisor más barato de **65 pulgadas** en Éxito. |
| `exito_tv_todos.py` | Ejecuta la comparativa simultánea de los 6 tamaños y exporta a CSV/JSON. |

---

## 💻 Instrucciones de Uso

```powershell
# Requisitos
py -m pip install playwright
py -m playwright install chromium

# Ejecutar el Top 10 general (Falabella & Éxito):
py scraper_tv.py

# Ejecutar el Top 10 de 50 pulgadas en adelante:
py scraper_tv.py --min-inches 50

# Ejecutar por tamaño específico en Éxito:
py exito_tv_43.py
py exito_tv_50.py
py exito_tv_55.py
py exito_tv_58.py
py exito_tv_60.py
py exito_tv_65.py

# Ejecutar todos los tamaños juntos en Éxito:
py exito_tv_todos.py
```
