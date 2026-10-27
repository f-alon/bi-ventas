# ⚡ LABFIX BI - Dashboard Operativo y Business Intelligence para Servicio Técnico de Celulares

Aplicación web modular de analítica y gestión operativa especializada en laboratorios de microelectrónica y reparación de smartphones.

---

## 🛠️ Stack Tecnológico
- **Frontend / Framework:** Python + Streamlit
- **Visualización Analítica:** Plotly (Plotly Graph Objects & Plotly Express) con tema Dark / Cyberpunk Slate personalizado
- **Base de Datos & Persistencia:** SQLite local (`data/repairs.db`) con transacciones ACID e índices
- **Procesamiento de Datos:** Pandas para series temporales, cálculos de márgenes y análisis de Pareto

---

## 🚀 Inicio Rápido (Doble Clic)
1. Haz doble clic en el archivo **`iniciar_dashboard.bat`**.
2. Automáticamente se abrirá en tu navegador web en `http://localhost:8501`.

---

## 📂 Arquitectura Modular

```text
e:\bi-ventas\
├── app.py                      # Punto de entrada, sidebar y orquestación de pestañas
├── iniciar_dashboard.bat       # Lanzador ejecutable con 1 doble clic para Windows
├── requirements.txt            # Dependencias del proyecto
├── core/
│   ├── config.py               # Catálogo de estados, marcas, modelos, fallas y paleta visual
│   ├── db.py                   # Esquema SQLite, consultas y operaciones CRUD
│   └── seed.py                 # Generador sintético de 180 órdenes de microelectrónica
├── components/
│   ├── ui.py                   # CSS avanzado y tipografía (Tema Dark / Cyberpunk Slate)
│   └── cards.py                # Tarjetas KPI con badges de variación y glow de neón
├── charts/
│   ├── theme.py                # Plantilla Plotly oscura unificada
│   ├── overview_charts.py      # Funnel operativo y carga de técnicos
│   ├── financial_charts.py     # Series temporales, matriz de rentabilidad y ticket medio
│   └── diagnostic_charts.py    # Sunburst jerárquico, Pareto 80/20 y retorno de garantías
└── views/
    ├── tab_overview.py         # Tab 1: Panel Ejecutivo y Operativo (WIP y alertas demoradas)
    ├── tab_financial.py        # Tab 2: Análisis Financiero, Costos y Márgenes
    ├── tab_diagnostics.py      # Tab 3: Métricas de Dispositivos, Fallas y Garantías
    ├── tab_explorer.py         # Tab 4: Explorador dinámico, auditoría y exportación CSV/Excel
    └── tab_ingestion.py        # Tab 5: Ingesta manual (Formulario OT) y Carga masiva (CSV/XLSX)
```

---

## 📊 Módulos del Dashboard

1. **Tab 1: Panel Ejecutivo y Operativo**
   - KPI Cards: Facturación mensual, Ganancia Neta mensual con variación intermensual (% MoM), Tasa de éxito técnico y Equipos en banco (WIP).
   - Funnel Operativo del ciclo de vida de órdenes.
   - Distribución de carga activa por técnico.
   - Tabla de **Alertas Críticas** para equipos demorados (> 5 días hábiles en banco sin cambio de estado).

2. **Tab 2: Análisis Financiero y Rentabilidad**
   - Evolución temporal de Facturación vs. Costos de Insumos vs. Margen Neto (agrupable por día, semana o mes).
   - Matriz de dispersión interactiva (Volumen vs. Margen promedio unitario por tipo de reparación).
   - Distribución de Ticket facturado con líneas de corte en media y mediana.
   - Tabla de desglose de margen porcentual.

3. **Tab 3: Métricas de Dispositivos y Fallas Frecuentes**
   - Sunburst jerárquico: `Marca → Modelo → Tipo de Falla`.
   - Análisis de Pareto (80/20) con frecuencia y curva acumulada.
   - Tasa de reingresos por garantía según categoría de servicio.
   - Top 10 modelos con mayor demanda en el laboratorio.

4. **Tab 4: Explorador y Auditoría (Data Explorer)**
   - Búsqueda global por texto (ID Orden, IMEI, Modelo, Cliente).
   - Filtros combinados por marca, técnico, categoría, estado y rango de precios.
   - Botones de exportación instantánea a formatos **CSV** y **Excel (.xlsx)**.

5. **Tab 5: Ingesta y Gestión Operativa**
   - **Carga Manual:** Formulario con cálculo automático de margen neto en tiempo real.
   - **Carga Masiva:** Validador de esquema de columnas y tipos de fecha con tabla previa y botón de confirmación.
   - Plantilla `.csv` descargable.

