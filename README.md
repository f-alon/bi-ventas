# ⚡ LABFIX BI - Dashboard Operativo y Business Intelligence para Servicio Técnico de Celulares

Aplicación web modular de analítica, Business Intelligence y gestión operativa especializada en laboratorios de microelectrónica y reparación de smartphones.

---

## 🛠️ Stack Tecnológico
- **Frontend / Framework:** Python + Streamlit
- **Seguridad & Autenticación:** PBKDF2-HMAC-SHA256 con salt criptográfico individual (100.000 rondas)
- **Visualización Analítica:** Plotly (Plotly Graph Objects & Plotly Express) con tema Dark / Cyberpunk Slate personalizado
- **Base de Datos & Persistencia:** SQLite local (`data/repairs.db`) con transacciones ACID, índices y parámetros seguros contra inyección SQL
- **Procesamiento de Datos:** Pandas para series temporales, cálculos de márgenes y análisis de Pareto

---

## 🚀 Inicio Rápido (Doble Clic)
1. Haz doble clic en el archivo **`iniciar_dashboard.bat`**.
2. Automáticamente se abrirá en tu navegador web en `http://localhost:8501`.
3. **Registro Inicial:** Si la base de datos está limpia a cero, la pantalla de **Onboarding** te solicitará registrar el usuario y contraseña del **Administrador Principal**.

---

## 👥 Roles y Paneles Diferenciados

### 🔬 Rol Técnico (Workspace de Banco de Trabajo)
- **Banco de Trabajo (WIP Kanban):** Visualiza exclusivamente sus órdenes asignadas en las etapas `Ingresado`, `En Diagnóstico`, `Esperando Repuesto` y `En Reparación`.
- **Actualización Rápida:** Cambia el estado de una reparación, anota mediciones de microelectrónica (ej. "Consumo 1.2A en VDD_MAIN") o carga número de tracking/proveedor de repuesto.
- **Derivación:** Botón para transferir una orden a otro colega (ej. derivar a reballing BGA).
- **Métricas Personales:** Reparaciones completadas en el mes, efectividad técnica (%), tiempo promedio de resolución (Lead Time en días), tasa de garantía personal y mano de obra facturada generada en su banco.
- **Alta Rápida de OTs:** Formulario donde el técnico asignado por defecto es el usuario logueado.

### 👑 Rol Administrador (Dashboard Global de BI)
- **Auditoría Global & Selector de Técnico:** Audita el taller completo o filtra todas las analíticas por un técnico específico.
- **5 Pestañas Analíticas:** Panel Ejecutivo (WIP general, alertas críticas > 5 días), Rentabilidad Financiera (Evolución, matriz de dispersión volumen vs. margen, ticket medio), Diagnósticos & Fallas (Sunburst, Pareto 80/20, garantías) y Explorador de Datos con exportación CSV/Excel.
- **Gestión de Personal:** Pestaña para dar de alta nuevos técnicos o administradores y gestionar bajas.
- **Control de Mantenimiento:** Herramienta integrada para purgar la base de datos a cero o sembrar 180 órdenes de prueba.

---

## 🧹 Reinicio Limpio de Base de Datos (Clean Reset)

Para purgar la base de datos desde la consola:

```bash
# 1. Purgar completamente a cero (0 órdenes y 0 usuarios):
python reset_db.py

# 2. Purgar órdenes a cero pero conservar los usuarios creados:
python reset_db.py --keep-users

# 3. Purgar y sembrar 180 órdenes sintéticas de prueba:
python reset_db.py --seed
```

---

## 📂 Arquitectura Modular

```text
e:\bi-ventas\
├── app.py                      # Puerta de enlace de autenticación, sidebar y ruteo por rol
├── auth.py                     # Hashing de contraseñas, login, registro y control de sesión
├── database.py                 # Conexión SQLite y funciones CRUD parametrizadas
├── reset_db.py                 # Script CLI independiente para purgar y reiniciar a cero
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
    ├── admin_view.py           # Vista del Administrador: BI global y gestión de equipo
    ├── tecnico_view.py         # Vista del Técnico: Banco WIP, métricas personales y notas
    ├── tab_overview.py         # Tab 1: Panel Ejecutivo y Operativo (WIP y demoras)
    ├── tab_financial.py        # Tab 2: Análisis Financiero, Costos y Márgenes
    ├── tab_diagnostics.py      # Tab 3: Métricas de Dispositivos, Fallas y Garantías
    ├── tab_explorer.py         # Tab 4: Explorador dinámico, auditoría y exportación CSV/Excel
    └── tab_ingestion.py        # Tab 5: Ingesta manual (Formulario OT) y Carga masiva (CSV/XLSX)
```
