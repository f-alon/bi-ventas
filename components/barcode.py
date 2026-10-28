"""Generador de Códigos de Barras (Code128B) y Formateador de Etiquetas Térmicas (58mm, 80mm, 40x25, 50x30)."""

from typing import Any, Dict, List

# Patrones de Code 128 (Subconjunto B para alfanumérico ASCII 32 a 126)
_CODE128_PATTERNS = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213", # 0-9
    "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132", # 10-19
    "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211", # 20-29
    "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313", # 30-39
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331", # 40-49
    "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111", # 50-59
    "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214", # 60-69
    "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111", # 70-79
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141", # 80-89
    "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141", # 90-99
    "114131", "311141", "411131", "211412", "211214", "211232", "2331112" # 100-106
]
_START_B = 104
_STOP = 106


def generate_code128_svg(text: str, bar_height: int = 50, bar_width: int = 2) -> str:
    """Genera código SVG nativo vectorial para el texto en Code 128B."""
    clean_text = str(text).strip()
    if not clean_text:
        clean_text = "N/A"

    values = [_START_B]
    checksum = _START_B

    for idx, char in enumerate(clean_text, start=1):
        code_val = ord(char) - 32
        if 0 <= code_val <= 95:
            values.append(code_val)
            checksum += code_val * idx
        else:
            # Reemplazar con espacio si no es imprimible
            values.append(0)

    check_digit = checksum % 103
    values.append(check_digit)
    values.append(_STOP)

    # Construir patrón de módulos (1 = barra, 0 = espacio)
    pattern_str = ""
    for v in values:
        pat = _CODE128_PATTERNS[v]
        is_bar = True
        for digit in pat:
            w = int(digit)
            pattern_str += ("1" if is_bar else "0") * w
            is_bar = not is_bar

    # Terminar con barra final
    pattern_str += "11"

    total_modules = len(pattern_str)
    svg_width = total_modules * bar_width
    svg_height = bar_height + 18

    rects = []
    current_x = 0
    for bit in pattern_str:
        if bit == "1":
            rects.append(f'<rect x="{current_x}" y="0" width="{bar_width}" height="{bar_height}" fill="#000000" />')
        current_x += bar_width

    rects_html = "\n".join(rects)

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}" style="display: block; margin: 0 auto; background: #FFFFFF;">
        {rects_html}
        <text x="{svg_width / 2}" y="{svg_height - 2}" text-anchor="middle" font-family="Courier, monospace" font-size="12" fill="#000000" font-weight="bold">{clean_text}</text>
    </svg>
    """
    return svg


def render_thermal_label_html(
    titulo: str,
    codigo_sku: str,
    precio: float,
    subtexto: str = "",
    preset: str = "58mm",
    precio_tecnicos: float | None = None,
) -> str:
    """Genera el HTML listo para imprimir en impresoras de etiquetas térmicas con CSS exacto."""
    presets_cfg = {
        "58mm": {"width": "210px", "padding": "8px", "font_title": "12px", "font_price": "15px", "bar_h": 40},
        "80mm": {"width": "290px", "padding": "12px", "font_title": "14px", "font_price": "18px", "bar_h": 48},
        "40x25mm": {"width": "160px", "padding": "5px", "font_title": "10px", "font_price": "13px", "bar_h": 30},
        "50x30mm": {"width": "200px", "padding": "6px", "font_title": "11px", "font_price": "14px", "bar_h": 36},
    }

    cfg = presets_cfg.get(preset, presets_cfg["58mm"])
    barcode_svg = generate_code128_svg(codigo_sku, bar_height=cfg["bar_h"], bar_width=2)

    precio_tec_html = ""
    if precio_tecnicos and precio_tecnicos > 0:
        precio_tec_html = f'<div style="font-size: 10px; color: #4B5563;">Gremio: <b>${precio_tecnicos:,.0f}</b></div>'

    html = f"""
    <div class="thermal-label-container" style="width: {cfg['width']}; background: #FFFFFF; color: #000000; padding: {cfg['padding']}; border: 1px dashed #9CA3AF; margin: 10px auto; text-align: center; font-family: 'Segoe UI', Tahoma, sans-serif; box-sizing: border-box;">
        <div style="font-size: {cfg['font_title']}; font-weight: 800; line-height: 1.2; max-height: 2.4em; overflow: hidden; text-transform: uppercase;">
            {titulo}
        </div>
        {f'<div style="font-size: 9px; color: #4B5563; margin-top: 2px;">{subtexto}</div>' if subtexto else ''}
        
        <div style="margin: 6px 0;">
            {barcode_svg}
        </div>

        <div style="font-size: {cfg['font_price']}; font-weight: 900; color: #000000; letter-spacing: -0.02em;">
            ${precio:,.0f}
        </div>
        {precio_tec_html}
    </div>
    """
    return html

