"""Configuraciones centrales, catálogos, navegación y constantes del ERP LABFIX."""

# Bloques operativos del menú de navegación ERP
NAV_MODULES = {
    "1. Operaciones & Taller": [
        ("oper_dashboard", "📊 Dashboard Principal", "Resumen ejecutivo en tiempo real, KPIs y timeline"),
        ("oper_ordenes", "🔧 Órdenes de Servicio", "Ciclo de vida de reparaciones, checklist de ingreso e insumos"),
        ("oper_cotizaciones", "📋 Cotizaciones / Presupuestos", "Emisión, aprobación, firma digital y conversión a remito"),
        ("oper_tecnicos", "🔬 Banco de Trabajo (Técnicos)", "Mesa de trabajo, notas de microelectrónica y autoasignación"),
        ("garantias_rma", "🛡️ Garantías & RMA", "Reclamos, órdenes derivadas sin costo ($0) y resolución"),
    ],
    "2. Mostrador & Comercial": [
        ("com_pos", "💳 Punto de Venta (POS)", "Facturación ágil de mostrador, multi-pago y tickets"),
        ("com_ventas", "🧾 Historial de Ventas", "Registro de ventas cerradas, detalle de ítems y reimpresión"),
        ("com_clientes", "👥 Directorio de Clientes", "Ficha 360°, historial de OTs, compras y cuenta corriente"),
        ("com_vendedores", "💼 Vendedores & Comisiones", "Gestión de personal comercial y liquidación de comisiones"),
        ("kiosco_leads", "📱 Leads & CRM / Kiosco", "Gestión de oportunidades de venta y terminal de autoservicio"),
    ],
    "3. Logística & Stock": [
        ("stock_inventario", "📦 Inventario & Variantes", "Control de stock, variantes por atributo y ajustes"),
        ("stock_etiquetas", "🏷️ Impresión de Etiquetas", "Generador de etiquetas térmicas y códigos de barra"),
        ("stock_proveedores", "🚚 Proveedores & Compras", "Directorio de distribuidores y control de compras"),
    ],
    "4. Finanzas & Caja": [
        ("fin_caja", "💵 Caja Diaria & Arqueo", "Apertura, arqueo ciego, gastos recurrentes y control de deuda"),
        ("fin_comprobantes", "📑 Comprobantes & Notas de Crédito", "Remitos oficiales y notas de crédito con compensación de deuda"),
        ("fin_reportes", "📈 Estado de Resultados (P&L) & BI", "P&L con CMV snapshot, gastos deducibles y margen neto"),
    ],
    "5. Administración & Sistema": [
        ("admin_config", "⚙️ Configuración del Taller & 2FA", "Organización, autenticación en 2 pasos y autoasignación"),
        ("admin_emails", "📧 Automatización de Emails", "Servidor SMTP y plantillas automáticas de estados de OT"),
        ("admin_soporte", "🛡️ Soporte & Auditoría", "Reporte de bugs, logs de auditoría y trazabilidad de acciones"),
    ],
}

# Roles de Usuario
ROLES = ["ADMIN", "TECNICO", "VENDEDOR"]

# Ciclo de vida estricto de Órdenes de Trabajo (OT)
ESTADOS_OT = [
    "PENDIENTE",
    "EN REPARACIÓN",
    "ESPERANDO REPUESTOS",
    "COMPLETADA",
    "ENTREGADA",
    "CANCELADA",
]

# Clasificaciones operativas
ESTADOS_WIP = [
    "PENDIENTE",
    "EN REPARACIÓN",
    "ESPERANDO REPUESTOS",
]
ESTADOS_TERMINADOS = ["COMPLETADA", "ENTREGADA", "CANCELADA"]
ESTADOS_EXITOSOS = ["COMPLETADA", "ENTREGADA"]

# Tipos de Dispositivo soportados
TIPOS_DISPOSITIVO = [
    "Smartphone",
    "Tablet",
    "Notebook",
    "Consola / Placa de Video",
    "Smartwatch / Wearable",
    "Otro",
]

# Plantillas de Checklist por Tipo de Dispositivo
CHECKLIST_TEMPLATES = {
    "Smartphone": [
        "Enciende",
        "Pantalla / Touch",
        "Tapa Trasera",
        "Chasis / Curvo",
        "Batería Hinchada",
        "Daño Líquido / Humedad",
        "Lector SIM / Señal",
        "Face ID / Huella",
        "Cámaras (Front/Tras)",
        "Parlante / Auricular / Mic",
        "Puerto de Carga",
        "Botones Físicos",
    ],
    "Tablet": [
        "Enciende",
        "Display / Vidrio Táctil",
        "Chasis / Esquinas",
        "Puerto de Carga",
        "Batería",
        "Botones Volumen / Power",
        "Cámara y Sensores",
        "Conectividad WiFi",
    ],
    "Notebook": [
        "Enciende / Da Video",
        "Bisagras / Flex Pantalla",
        "Teclado / Touchpad",
        "Cargador Original Dejado",
        "Batería Operativa",
        "Puertos USB / HDMI",
        "Tornillería Completa",
        "Signos de Líquido",
    ],
    "Consola / Placa de Video": [
        "Enciende / Luces LED",
        "Salida de Video HDMI",
        "Ventiladores / Cooler",
        "Alimentación / Fuente",
        "Conectores PCIe / Pines",
        "Lector Óptico / Disco",
        "Tornillos Originales",
    ],
    "Otro": [
        "Enciende",
        "Estado Físico General",
        "Accesorios Incluidos",
        "Signos de Humedad",
    ],
}

# Categorías de stock
CATEGORIAS_STOCK = [
    "Repuestos",
    "Accesorios",
    "Herramientas/Insumos",
]

SUBCATEGORIAS_STOCK = {
    "Repuestos": [
        "Módulos / Displays OLED",
        "Baterías",
        "Pines / Flex de Carga",
        "ICs & Componentes SMD",
        "Cámaras & Sensores",
        "Tapas traseras & Chasis",
    ],
    "Accesorios": [
        "Fundas & Carcasas",
        "Vidrios Templados / Hidrogel",
        "Cables USB & Adaptadores",
        "Cargadores de Pared",
        "Auriculares & Audio",
    ],
    "Herramientas/Insumos": [
        "Flux & Estaño en Pasta",
        "Alcohol Isopropílico",
        "Mallas para desoldar",
        "Puntas de Cautín / Stencils",
        "Adhesivos & Cintas B7000/T7000",
    ],
}

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
    "Mantenimiento General / Limpieza",
]

# Métodos de Pago estándar
METODOS_PAGO = [
    "Efectivo",
    "Transferencia / Alias",
    "Débito",
    "Crédito",
    "Mercado Pago",
    "Cuenta Corriente",
    "Otro",
]

# Alícuotas de IVA por defecto
ALICUOTAS_IVA = [0.0, 10.5, 21.0, 27.0]

# Estados de Cotizaciones
ESTADOS_COTIZACION = [
    "BORRADOR",
    "ENVIADA",
    "ACEPTADA",
    "RECHAZADA",
]

# Estados de Garantía RMA
ESTADOS_GARANTIA = [
    "PENDIENTE",
    "EN REVISIÓN",
    "ACEPTADO",
    "RECHAZADO",
    "RESUELTO",
]

# Estados de Leads
ESTADOS_LEADS = [
    "NUEVO",
    "CONTACTADO",
    "CALIFICADO",
    "CONVERTIDO",
    "DESCARTADO",
]

# Frecuencias de Gasto Recurrente
FRECUENCIAS_GASTO = ["SEMANAL", "MENSUAL", "ANUAL"]

# Marcas de dispositivos
MARCAS = ["Apple", "Samsung", "Xiaomi", "Motorola", "Google", "Huawei", "Sony", "Lenovo", "Dell", "HP", "Asus", "Nintendo", "Otro"]

# Catálogo referencial de modelos
MODELOS_POR_MARCA = {
    "Apple": [
        "iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15", "iPhone 14 Pro Max", "iPhone 14 Pro",
        "iPhone 14", "iPhone 13 Pro Max", "iPhone 13 Pro", "iPhone 13", "iPhone 12 Pro", "iPhone 12",
        "iPhone 11", "iPhone XR", "iPhone X", "iPad Pro 11", "iPad Air 5", "MacBook Air M2", "MacBook Pro M1",
    ],
    "Samsung": [
        "Galaxy S24 Ultra", "Galaxy S24+", "Galaxy S24", "Galaxy S23 Ultra", "Galaxy S23",
        "Galaxy S22", "Galaxy S21 FE", "Galaxy A55", "Galaxy A54 5G", "Galaxy A34", "Galaxy A14",
        "Galaxy Z Fold 5", "Galaxy Z Flip 5", "Galaxy Tab S9",
    ],
    "Xiaomi": [
        "Xiaomi 13 Pro", "Xiaomi 12", "Redmi Note 13 Pro+", "Redmi Note 13", "Redmi Note 12 Pro",
        "Redmi Note 11", "Redmi 12", "POCO F5 Pro", "POCO X5 Pro", "POCO M5",
    ],
    "Motorola": [
        "Edge 40 Pro", "Edge 40 Neo", "Edge 30 Ultra", "Moto G84 5G", "Moto G54", "Moto G23",
        "Moto G13", "Moto E22", "Razr 40 Ultra",
    ],
    "Sony": ["PlayStation 5", "PlayStation 4 Pro", "PlayStation 4 Slim", "Xperia 1 V"],
    "Nintendo": ["Switch OLED", "Switch V2", "Switch Lite"],
    "Otro": ["Genérico / Sin catálogo"],
}

# Paleta de Colores Dark / Cyberpunk
COLORS = {
    "bg_dark": "#0B0F19",
    "card_bg": "#111827",
    "card_border": "#1F2937",
    "cyan": "#00F0FF",
    "green": "#10B981",
    "purple": "#8B5CF6",
    "yellow": "#F59E0B",
    "red": "#F43F5E",
    "text_primary": "#FFFFFF",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6B7280",
}
