"""Consultas de sólo lectura para trazabilidad del flujo de trabajo.

Reciben una conexión sqlite3 explícita (en vez de usar la conexión global de
la app) para poder ejecutarse tanto contra la base local como contra un
archivo pae.db importado de otra máquina para revisión.
"""

from __future__ import annotations

import sqlite3


def list_imported_files(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Archivos Excel importados: cuándo, por qué Agente, para qué Abogado."""
    return conn.execute(
        """
        SELECT f.id, f.original_filename, f.row_count, f.imported_at,
               au.full_name AS agente_nombre, au.username AS agente_usuario,
               bu.full_name AS abogado_nombre, bu.username AS abogado_usuario
        FROM imported_files f
        LEFT JOIN users au ON au.id = f.agente_id
        LEFT JOIN users bu ON bu.id = f.abogado_id
        ORDER BY f.imported_at DESC
        """
    ).fetchall()


def list_batches(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Lotes de Requerimientos: estado y avance de captura por Agente/Abogado."""
    return conn.execute(
        """
        SELECT b.id, b.status, b.created_at, b.updated_at,
               au.full_name AS agente_nombre, au.username AS agente_usuario,
               bu.full_name AS abogado_nombre, bu.username AS abogado_usuario,
               (SELECT COUNT(*) FROM requerimiento_rows r WHERE r.batch_id = b.id) AS total_filas,
               (SELECT COUNT(*) FROM requerimiento_rows r WHERE r.batch_id = b.id
                    AND r.fecha_notificacion IS NOT NULL AND r.quien_recibe IS NOT NULL) AS filas_capturadas
        FROM requerimiento_batches b
        LEFT JOIN users au ON au.id = b.agente_id
        LEFT JOIN users bu ON bu.id = b.abogado_id
        ORDER BY b.created_at DESC
        """
    ).fetchall()


def list_mandamiento_imported_files(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Igual que `list_imported_files`, para Mandamiento."""
    return conn.execute(
        """
        SELECT f.id, f.original_filename, f.row_count, f.imported_at,
               au.full_name AS agente_nombre, au.username AS agente_usuario,
               bu.full_name AS abogado_nombre, bu.username AS abogado_usuario
        FROM mandamiento_imported_files f
        LEFT JOIN users au ON au.id = f.agente_id
        LEFT JOIN users bu ON bu.id = f.abogado_id
        ORDER BY f.imported_at DESC
        """
    ).fetchall()


def list_mandamiento_batches(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Lotes de Mandamientos: igual que `list_batches`, para Mandamiento."""
    return conn.execute(
        """
        SELECT b.id, b.status, b.created_at, b.updated_at,
               au.full_name AS agente_nombre, au.username AS agente_usuario,
               bu.full_name AS abogado_nombre, bu.username AS abogado_usuario,
               (SELECT COUNT(*) FROM mandamiento_rows r WHERE r.batch_id = b.id) AS total_filas,
               (SELECT COUNT(*) FROM mandamiento_rows r WHERE r.batch_id = b.id
                    AND r.fecha_notificacion IS NOT NULL AND r.quien_recibe IS NOT NULL) AS filas_capturadas
        FROM mandamiento_batches b
        LEFT JOIN users au ON au.id = b.agente_id
        LEFT JOIN users bu ON bu.id = b.abogado_id
        ORDER BY b.created_at DESC
        """
    ).fetchall()
