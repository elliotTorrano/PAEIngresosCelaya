# Historial de versiones — Sistema PAE

## 0.2.0

- El Súper-usuario y el Administrador ya no se crean con un asistente interactivo:
  se siembran automáticamente y en silencio desde `resources/seed_accounts.json`
  la primera vez que faltan en la base de datos local. Como ese archivo se
  empaqueta con el programa, la cuenta creada es siempre la misma sin importar
  en qué máquina o cuántas veces se ejecute el `.exe` — nunca se vuelve a pedir.
  **Antes de generar el `.exe` para distribuir, edítese ese archivo con los
  datos reales.**
- El Abogado debe cambiar su contraseña obligatoriamente la primera vez que
  inicia sesión (o después de que el Administrador le asigna una nueva por un
  reset), mediante un diálogo que no se puede omitir.
- En las pantallas de login (usuario, contraseña y certificado) la tecla Enter
  ahora dispara el botón "Iniciar sesión"/"Continuar" correspondiente.

## 0.1.0

Primera fase del programa:

- Login con 3 niveles de rol (Súper-usuario, Administrador, Agente del PAE, Abogado).
- Certificado digital autofirmado (.pfx) para Súper-usuario/Administrador/Agentes; usuario y contraseña para Abogados.
- Asistente de primer arranque: crea al único Súper-usuario y al primer (único) Administrador.
- Recuperación de acceso por archivo de solicitud + correo al Administrador, y paquete de actualización de credenciales para aplicar en la instalación del solicitante.
- Gestión de Agentes del PAE y Abogados por el Administrador.
- Apariencia personalizable (ícono de ventana y fondo) por el Administrador.
- Formato de Requerimientos completo:
  - Agente del PAE: selección de abogado, carga de Excel con aviso de duplicados por nombre de archivo, conteo acumulado de filas, vista previa y exportación.
  - Abogado: importación del archivo del Agente (sin poder modificar sus datos), captura de "Fecha de Notificación de citatorio" y "Quién recibe el citatorio" (con mayúsculas automáticas), botón para resaltar la primera fila pendiente de captura, y exportación final.
- Formato de Mandamientos y los Reportes de Requerimientos/Mandamientos quedan como fase pendiente.
