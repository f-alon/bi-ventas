"""Configuraciones, constantes y catálogo de valores del taller."""

# Estados del ciclo de vida de la orden
ESTADOS_ORDEN = [
    "Ingresado",
    "En Diagnóstico",
    "Esperando Repuesto",
    "En Reparación",
    "Listo para Entrega",
    "Entregado",
    "Sin Reparación / Rechazado",
]

# Clasificación operativa
ESTADOS_WIP = ["Ingresado", "En Diagnóstico", "Esperando Repuesto", "En Reparación"]
ESTADOS_TERMINADOS = ["Listo para Entrega", "Entregado", "Sin Reparación / Rechazado"]
ESTADOS_EXITOSOS = ["Listo para Entrega", "Entregado"]

# Categorías de fallas de servicio técnico
CATEGORIAS_FALLA = [
    "Pantalla / Módulo",
    "Batería",
    "Puerto de carga",
    "Placa base / Microelectrónica (IC Power, corto, VDD/VCC)",
    "Reballing (CPU / RAM / Baseband)",
    "Daño por líquido",
    "Software / FRP",
    "Cámara / Audio / Sensores",
]

# Marcas y modelos frecuentes
MARCAS = ["Apple", "Samsung", "Xiaomi", "Motorola", "Google", "Huawei"]

MODELOS_POR_MARCA = {
    "Apple": [
        "iPhone 11",
        "iPhone 12",
        "iPhone 12 Pro",
        "iPhone 13",
        "iPhone 13 Pro Max",
        "iPhone 14",
        "iPhone 14 Pro Max",
        "iPhone 15",
        "iPhone 15 Pro",
        "iPad 9na Gen",
        "iPad Air 4",
    ],
    "Samsung": [
        "Galaxy A14",
        "Galaxy A34",
        "Galaxy A54",
        "Galaxy S21 FE",
        "Galaxy S22 Ultra",
        "Galaxy S23",
        "Galaxy S23 Ultra",
        "Galaxy Z Flip 4",
        "Galaxy Note 20 Ultra",
    ],
    "Xiaomi": [
        "Redmi 10C",
        "Redmi Note 11",
        "Redmi Note 12",
        "Redmi Note 12 Pro 5G",
        "Poco X3 Pro",
        "Poco X5 Pro",
        "Poco F4",
        "Xiaomi 12 Lite",
    ],
    "Motorola": [
        "Moto G22",
        "Moto G52",
        "Moto G84 5G",
        "Moto Edge 30",
        "Moto Edge 40 Neo",
        "Moto E22",
    ],
    "Google": [
        "Pixel 6",
        "Pixel 6a",
        "Pixel 7",
        "Pixel 7 Pro",
        "Pixel 8",
    ],
    "Huawei": [
        "P30 Lite",
        "P40 Pro",
        "Nova 9",
        "Y9 Prime",
    ],
}

TECNICOS = [
    "Lucas M. (Microelectrónica N3)",
    "Sofía G. (Hardware & Displays)",
    "Martín V. (Diagnóstico & Software)",
    "Gonzalo R. (Reballing & Soldadura)",
]

GARANTIAS_DIAS = [0, 30, 60, 90, 180]

# Paleta técnica de diseño (Dark / Cyberpunk Slate)
COLORS = {
    "bg_dark": "#0B0F19",
    "card_bg": "#111827",
    "card_border": "#1F2937",
    "cyan": "#00F0FF",
    "emerald": "#10B981",
    "amber": "#F59E0B",
    "rose": "#F43F5E",
    "purple": "#8B5CF6",
    "blue": "#3B82F6",
    "text_primary": "#F9FAFB",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6B7280",
}

