"""Generador de Comprobantes, Remitos con Cláusulas de Garantía y Tickets Térmicos."""

from datetime import date
from typing import Any, Dict, List
import streamlit as st
from components.cards import format_currency


def render_repair_delivery_remito(order: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Genera el HTML imprimible del Remito de Entrega con términos legales y garantía."""
    taller_nombre = config.get("nombre_taller", "LABFIX Microelectrónica")
    taller_cuit = config.get("cuit", "")
    taller_dir = config.get("direccion", "")
    taller_tel = config.get("telefono", "")
    terminos = config.get("terminos_legales", "Garantía cubre exclusivamente los componentes reemplazados y la mano de obra aplicada.")

    garantia_dias = int(order.get("garantia_dias", 60))
    total = float(order.get("total", 0.0))
    saldo = float(order.get("saldo_pendiente", 0.0))
    seña = float(order.get("monto_senado", 0.0))

    html = f"""
    <div style="background: #FFFFFF; color: #111827; padding: 25px; border-radius: 8px; font-family: 'Courier New', Courier, monospace; border: 2px dashed #9CA3AF; max-width: 680px; margin: 15px auto;">
        <div style="text-align: center; border-bottom: 2px solid #111827; padding-bottom: 10px;">
            <h2 style="margin: 0; font-size: 20px; font-weight: 800; color: #111827;">{taller_nombre.upper()}</h2>
            <div style="font-size: 11px;">CUIT: {taller_cuit} | {taller_dir}</div>
            <div style="font-size: 11px;">TEL: {taller_tel}</div>
            <div style="margin-top: 6px; font-weight: bold; font-size: 14px; background: #E5E7EB; padding: 3px; border-radius: 4px;">
                REMITO DE ENTREGA & CERTIFICADO DE GARANTÍA #{order.get('ot_codigo', 'OT-XXXX')}
            </div>
        </div>

        <div style="display: flex; justify-content: space-between; font-size: 12px; margin-top: 15px;">
            <div>
                <b>CLIENTE:</b> {order.get('cliente_nombre', 'Consumidor Final')}<br>
                <b>DNI/CUIT:</b> {order.get('cliente_dni', 'S/D')}<br>
                <b>TELÉFONO:</b> {order.get('cliente_telefono', 'S/D')}
            </div>
            <div style="text-align: right;">
                <b>FECHA INGRESO:</b> {order.get('fecha_ingreso', '')}<br>
                <b>FECHA ENTREGA:</b> {order.get('fecha_egreso', str(date.today()))}<br>
                <b>ESTADO:</b> {order.get('estado', 'Entregado')}
            </div>
        </div>

        <div style="margin-top: 15px; border: 1px solid #D1D5DB; padding: 10px; border-radius: 4px; font-size: 12px; background: #F9FAFB;">
            <b>EQUIPO:</b> {order.get('marca', '')} {order.get('modelo', '')} | <b>IMEI/SERIE:</b> {order.get('imei_serie', 'S/N')}<br>
            <b>FALLA REPORTADA:</b> {order.get('falla_declarada', '')}<br>
            <b>TRABAJO REALIZADO:</b> {order.get('diagnostico_tecnico', 'Reparación de hardware / microelectrónica')}
        </div>

        <div style="margin-top: 15px; font-size: 13px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #111827;">
                    <th style="text-align: left; padding: 4px 0;">CONCEPTO</th>
                    <th style="text-align: right; padding: 4px 0;">IMPORTE</th>
                </tr>
                <tr>
                    <td style="padding: 4px 0;">Mano de Obra Especializada</td>
                    <td style="text-align: right; padding: 4px 0;">{format_currency(order.get('mano_obra', 0))}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0;">Repuestos e Insumos Imputados</td>
                    <td style="text-align: right; padding: 4px 0;">{format_currency(order.get('costo_repuestos', 0))}</td>
                </tr>
                <tr style="border-top: 1px dashed #9CA3AF;">
                    <td style="padding: 4px 0;"><b>TOTAL REPARACIÓN:</b></td>
                    <td style="text-align: right; padding: 4px 0;"><b>{format_currency(total)}</b></td>
                </tr>
                <tr>
                    <td style="padding: 2px 0; color: #4B5563;">Seña previa abonada:</td>
                    <td style="text-align: right; padding: 2px 0; color: #4B5563;">- {format_currency(seña)}</td>
                </tr>
                <tr style="font-size: 14px; background: #F3F4F6;">
                    <td style="padding: 6px 4px;"><b>SALDO FINAL ABONADO:</b></td>
                    <td style="text-align: right; padding: 6px 4px;"><b>{format_currency(saldo if saldo > 0 else total)}</b></td>
                </tr>
            </table>
        </div>

        <div style="margin-top: 15px; border-top: 1px solid #111827; padding-top: 8px; font-size: 10px; color: #374151;">
            <b>PLAZO DE GARANTÍA LEGAL OTORGADO: {garantia_dias} DÍAS CORRIDOS</b><br>
            <i>{terminos}</i>
        </div>

        <div style="margin-top: 35px; display: flex; justify-content: space-around; text-align: center; font-size: 11px;">
            <div style="border-top: 1px solid #111827; width: 200px; padding-top: 5px;">
                Firma Responsable Taller
            </div>
            <div style="border-top: 1px solid #111827; width: 200px; padding-top: 5px;">
                Firma y Aclaración Cliente (Conforme)
            </div>
        </div>
    </div>
    """
    return html


def render_pos_ticket_receipt(sale: Dict[str, Any], items: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    """Genera formato ticket térmico de mostrador para el Punto de Venta."""
    taller_nombre = config.get("nombre_taller", "LABFIX Store")
    taller_cuit = config.get("cuit", "")
    taller_dir = config.get("direccion", "")
    taller_tel = config.get("telefono", "")

    items_rows = ""
    for it in items:
        sub = float(it["precio_unitario"]) * int(it["cantidad"])
        items_rows += f"""
        <tr>
            <td style="padding: 3px 0;">{it.get('nombre', 'Producto')} x{it['cantidad']}</td>
            <td style="text-align: right; padding: 3px 0;">{format_currency(sub)}</td>
        </tr>
        """

    html = f"""
    <div style="background: #FFFFFF; color: #000000; padding: 18px; border-radius: 6px; font-family: 'Courier New', monospace; width: 340px; margin: 10px auto; border: 1px solid #9CA3AF; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
        <div style="text-align: center; border-bottom: 1px dashed #000; padding-bottom: 8px;">
            <b style="font-size: 15px;">{taller_nombre.upper()}</b><br>
            <span style="font-size: 10px;">CUIT: {taller_cuit} | {taller_dir}</span><br>
            <span style="font-size: 10px;">TEL: {taller_tel}</span><br>
            <span style="font-size: 11px; font-weight: bold; margin-top: 4px; display: block;">TICKET DE VENTA #{sale.get('numero_ticket', 'TCK-XXXX')}</span>
            <span style="font-size: 10px;">{sale.get('creado_en', str(date.today()))}</span>
        </div>

        <div style="font-size: 11px; margin-top: 8px;">
            <b>CLIENTE:</b> {sale.get('cliente_nombre', 'Consumidor Final')}<br>
            <b>MEDIO PAGO:</b> {sale.get('metodo_pago', 'Efectivo')}
        </div>

        <div style="border-top: 1px dashed #000; border-bottom: 1px dashed #000; margin: 8px 0; padding: 6px 0;">
            <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
                {items_rows}
            </table>
        </div>

        <div style="font-size: 12px; line-height: 1.4;">
            <div style="display: flex; justify-content: space-between;">
                <span>Subtotal:</span>
                <span>{format_currency(sale.get('subtotal', 0))}</span>
            </div>
            {f'<div style="display: flex; justify-content: space-between; color: #DC2626;"><span>Descuento:</span><span>-{format_currency(sale.get("descuento", 0))}</span></div>' if sale.get('descuento', 0) > 0 else ''}
            {f'<div style="display: flex; justify-content: space-between;"><span>Recargo:</span><span>+{format_currency(sale.get("recargo", 0))}</span></div>' if sale.get('recargo', 0) > 0 else ''}
            <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 14px; border-top: 1px solid #000; padding-top: 4px; margin-top: 4px;">
                <span>TOTAL:</span>
                <span>{format_currency(sale.get('total', 0))}</span>
            </div>
        </div>

        <div style="text-align: center; font-size: 9px; margin-top: 12px; border-top: 1px dashed #000; padding-top: 6px;">
            ¡Gracias por su compra!<br>Conserve este ticket para cualquier cambio dentro de las 72 hs.
        </div>
    </div>
    """
    return html

