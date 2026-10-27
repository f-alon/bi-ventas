"""Generador de datos sintéticos hiperrealistas de microelectrónica y reparación de celulares."""

from datetime import date, timedelta
import random
import pandas as pd
from core.config import CATEGORIAS_FALLA, ESTADOS_ORDEN, MARCAS, MODELOS_POR_MARCA, TECNICOS
from core.db import bulk_insert_orders, get_connection, init_db

CLIENTES_NOMBRES = [
    "Alejandro Gómez", "Valeria Rossi", "Federico Benítez", "Camila Fernández",
    "Esteban Morales", "Lucía Díaz", "Mariano Castro", "Florencia Romero",
    "Agustín Navarro", "Julieta Álvarez", "Nicolás Torres", "Carolina Méndez",
    "Sebastián Ruiz", "Paula Bianchi", "Rodrigo Vega", "Martina Silva",
    "Ignacio Ortiz", "Daniela Herrera", "Facundo Cabrera", "Micaela Paz",
]

DIAGNOSTICOS = {
    "Placa base / Microelectrónica (IC Power, corto, VDD/VCC)": [
        "Cortocircuito en línea principal VDD_MAIN. Se aisló y reemplazó capacitor cerámico en fuga C3205.",
        "Falla de encendido. Consumo fijo de 80mA en fuente regulada. Reemplazo de PMIC principal.",
        "Sin carga ni detección USB. Reemplazo de circuito integrado Tristar/Hydra (1612A1).",
        "Sin audio en llamadas ni altavoz. Desprendimiento de pads en Audio Codec. Se reconstruyó jumper y soldadura.",
        "Consumo secundario tras botón de encendido. Reemplazo de bobina L5001 y diodo de protección.",
    ],
    "Reballing (CPU / RAM / Baseband)": [
        "Equipo reinicia en logo (Bootloop) característico. Reballing de memoria RAM/SoC con estaño con plomo 183°C.",
        "Sin señal / Error de Baseband 'Sin servicio'. Se levantó IC módem, limpieza de pads y reballing con stencil.",
        "Poco X3 Pro con pantalla en blanco/negro súbita. Reballing conjunto CPU + RAM exitoso.",
    ],
    "Pantalla / Módulo": [
        "Cristal y panel OLED estallado por impacto severo. Cambio de módulo completo Service Pack con adhesivo estanco.",
        "Touch intermitente con líneas verdes verticales. Reemplazo de display original ensamblado con marco.",
        "Módulo genérico previo dañado. Instalación de display OLED premium con reprogramación TrueTone.",
    ],
    "Batería": [
        "Degradación química de celda al 68%, reinicios inesperados con 20%. Instalación de celda nueva de alta capacidad.",
        "Batería hinchada que generó levantamiento de tapa trasera. Extracción segura y sellado perimetral.",
    ],
    "Puerto de carga": [
        "Flex Sub-Main dañado y pines sulfatados. Reemplazo de placa de carga original con soporte Fast Charge.",
        "Alerta permanente de 'Humedad detectada en puerto'. Reemplazo de conector Type-C bajo microscopio.",
    ],
    "Daño por líquido": [
        "Caída en agua clorada. Limpieza química en batea de ultrasonido con alcohol isopropílico y reconstrucción de pistas.",
        "Sulfato severo en zona de backlight y conector FPC de pantalla. Limpieza y cambio de conector FPC.",
    ],
    "Software / FRP": [
        "Bucle de reinicio tras actualización OTA corrupta. Flash completo de firmware stock multiapps vía cable EDL.",
        "Equipo bloqueado por cuenta Google posterior a hard reset. Desbloqueo y saneamiento de partición persist.",
    ],
    "Cámara / Audio / Sensores": [
        "Cámara principal no enfoca y emite zumbido ultrasónico por OIS quebrado. Reemplazo de módulo óptico.",
        "Altavoz inferior con sonido distorsionado y sin vibrador háptico. Reemplazo de buzzer.",
    ],
}

COSTOS_PRECIOS = {
    "Placa base / Microelectrónica (IC Power, corto, VDD/VCC)": (12000, 22000, 65000, 135000),
    "Reballing (CPU / RAM / Baseband)": (15000, 28000, 85000, 160000),
    "Pantalla / Módulo": (28000, 85000, 58000, 145000),
    "Batería": (12000, 25000, 29000, 60000),
    "Puerto de carga": (5000, 14000, 22000, 48000),
    "Daño por líquido": (10000, 20000, 50000, 95000),
    "Software / FRP": (2000, 6000, 25000, 50000),
    "Cámara / Audio / Sensores": (9000, 22000, 32000, 65000),
}


def seed_database(num_records: int = 180, force: bool = False) -> int:
    """Siembra la base de datos con órdenes históricas y activas."""
    init_db()
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0]

    if count > 0 and not force:
        return count

    if force:
        with conn:
            conn.execute("DELETE FROM ordenes;")

    random.seed(42)
    today = date.today()
    rows = []

    for i in range(1, num_records + 1):
        ot_id = f"OT-{1000 + i}"
        days_ago = random.randint(0, 120)
        f_ingreso = today - timedelta(days=days_ago)

        marca = random.choices(
            MARCAS,
            weights=[35, 30, 18, 12, 3, 2],
            k=1,
        )[0]
        modelo = random.choice(MODELOS_POR_MARCA[marca])

        categoria = random.choices(
            CATEGORIAS_FALLA,
            weights=[25, 18, 14, 16, 8, 7, 7, 5],
            k=1,
        )[0]

        diag_list = DIAGNOSTICOS.get(categoria, ["Revisión técnica de componentes."])
        diagnostico = random.choice(diag_list)

        cost_min, cost_max, price_min, price_max = COSTOS_PRECIOS[categoria]
        costo = round(random.uniform(cost_min, cost_max), -2)
        cobrado = round(random.uniform(price_min, price_max), -2)
        if cobrado < costo:
            cobrado = round(costo * 1.6, -2)

        # Estado según antigüedad
        if days_ago > 14:
            estado = random.choices(
                ["Entregado", "Listo para Entrega", "Sin Reparación / Rechazado"],
                weights=[84, 8, 8],
                k=1,
            )[0]
        elif days_ago > 4:
            estado = random.choices(
                ESTADOS_ORDEN,
                weights=[6, 10, 14, 18, 16, 30, 6],
                k=1,
            )[0]
        else:
            estado = random.choices(
                ["Ingresado", "En Diagnóstico", "Esperando Repuesto", "En Reparación"],
                weights=[35, 30, 20, 15],
                k=1,
            )[0]

        # Fechas de egreso y último cambio de estado
        if estado in ["Entregado", "Listo para Entrega"]:
            lead_days = random.randint(1, min(max(days_ago, 1), 8))
            f_egreso = f_ingreso + timedelta(days=lead_days)
            f_ultimo = f_egreso
        elif estado == "Sin Reparación / Rechazado":
            lead_days = random.randint(1, min(max(days_ago, 1), 4))
            f_egreso = f_ingreso + timedelta(days=lead_days)
            f_ultimo = f_egreso
            # Si fue rechazado sin reparacion, no se cobra mano de obra (solo presupuesto o costo nulo)
            cobrado = round(random.choice([0.0, 5000.0, 8000.0]), -2)
            costo = 0.0
        else:
            f_egreso = None
            # Para simular alertas de órdenes demoradas (> 5 días en WIP)
            if random.random() < 0.28:
                f_ultimo = f_ingreso  # lleva sin moverse desde que ingresó
            else:
                f_ultimo = min(today, f_ingreso + timedelta(days=random.randint(0, max(days_ago, 0))))

        tecnico = random.choice(TECNICOS)
        garantia = random.choice([30, 60, 90])
        # Retorno de garantía realista (aprox 4.5% de entregados)
        es_retorno = 1 if (estado == "Entregado" and random.random() < 0.05) else 0

        imei = f"35{random.randint(1000000000000, 9999999999999)}"
        cliente = random.choice(CLIENTES_NOMBRES)
        telefono = f"+54 9 11 {random.randint(4000, 8999)}-{random.randint(1000, 9999)}"

        rows.append(
            {
                "id_orden": ot_id,
                "fecha_ingreso": str(f_ingreso),
                "fecha_egreso": str(f_egreso) if f_egreso else "",
                "fecha_ultimo_estado": str(f_ultimo),
                "cliente_nombre": cliente,
                "cliente_telefono": telefono,
                "imei": imei,
                "marca": marca,
                "modelo": modelo,
                "categoria_falla": categoria,
                "diagnostico": diagnostico,
                "costo_repuesto": costo,
                "valor_cobrado": cobrado,
                "estado": estado,
                "tecnico": tecnico,
                "garantia_dias": garantia,
                "es_retorno_garantia": es_retorno,
            }
        )

    df_seed = pd.DataFrame(rows)
    inserted = bulk_insert_orders(df_seed)
    return inserted

