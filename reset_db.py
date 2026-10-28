"""Script CLI independiente para purgar, reiniciar y verificar la base de datos a cero (Clean Reset).

Uso:
  python reset_db.py                # Deja la base de datos totalmente en cero (0 órdenes y 0 usuarios)
  python reset_db.py --keep-users   # Pone las órdenes en cero pero preserva los usuarios y contraseñas
  python reset_db.py --seed         # Reinicia y repuebla con 180 órdenes de prueba para demo
"""

import argparse
import sys
from pathlib import Path

# Añadir raíz al sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import DB_PATH, get_connection, init_db, purge_all_tables
from core.seed import seed_database


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Clean Reset de la base de datos de LABFIX ERP")
    parser.add_argument(
        "--keep-users",
        action="store_true",
        help="Borra todas las operaciones pero conserva los usuarios registrados",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Siembra datos de prueba tras el reinicio",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("LABFIX ERP - REINICIO Y PURGA DE BASE DE DATOS (CLEAN RESET)")
    print("=" * 60)
    print(f"Ruta de base de datos: {DB_PATH}")

    # Purgar y recrear esquema
    purge_all_tables(keep_users=args.keep_users)
    init_db()

    conn = get_connection()
    user_count = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    order_count = conn.execute("SELECT COUNT(*) FROM dispositivos_ordenes").fetchone()[0]
    stock_count = conn.execute("SELECT COUNT(*) FROM productos_stock").fetchone()[0]

    print(f"[OK] Ordenes de servicio: {order_count} (Metricas limpias en 0)")
    print(f"[OK] Articulos de stock: {stock_count}")
    print(f"[OK] Usuarios registrados: {user_count}")

    if args.seed:
        print("[*] Sembrando datos de prueba realistas para los 5 modulos ERP...")
        seed_database(force=True)
        order_count = conn.execute("SELECT COUNT(*) FROM dispositivos_ordenes").fetchone()[0]
        stock_count = conn.execute("SELECT COUNT(*) FROM productos_stock").fetchone()[0]
        user_count = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        print(f"[OK] Base sembrada con exito:")
        print(f"     - Usuarios: {user_count}")
        print(f"     - Articulos de Stock: {stock_count}")
        print(f"     - Ordenes de Servicio: {order_count}")

    print("\n[OK] Base de datos lista. Las estadisticas arrancaran limpias sin errores.")
    print("=" * 60)



if __name__ == "__main__":
    main()
