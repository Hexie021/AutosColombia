# Autos Colombia — EA1

Este proyecto corresponde a la primera iteración del sistema de información del parqueadero Autos Colombia. En esta entrega nos centramos en la **gestión de la entrada y salida de vehículos**, de acuerdo con el alcance de la EA1.

Partimos del repositorio compartido por el profesor y complementamos lo necesario para esta operación. El backend está desarrollado con FastAPI y SQLAlchemy, el frontend con Angular y la base de datos con PostgreSQL. Para crear y actualizar las tablas utilizamos las migraciones de Alembic.

La gestión completa de usuarios, celdas y pagos se continuará en las siguientes entregas. Por ahora contamos con los datos mínimos de clientes, vehículos, mensualidades, celdas y operadores para que el registro de entradas y salidas funcione.

## Qué necesitamos para ejecutarlo

- Windows con Python 3.13 o 3.14.
- Node.js 24, con una versión mínima de 24.15.
- PostgreSQL 18 instalado y en ejecución.
- Git para descargar el repositorio.

También podemos utilizar pgAdmin para revisar las tablas y sus relaciones, aunque no es necesario tenerlo abierto para usar la aplicación.

Los comandos de preparación se ejecutan en PowerShell, desde la carpeta principal del repositorio.

## Instalación del proyecto

Primero descargamos el repositorio, creamos el entorno virtual de Python e instalamos las dependencias de ambos proyectos:

```powershell
git clone https://github.com/Hexie021/AutosColombia.git
cd AutosColombia
py -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

El entorno virtual mantiene las dependencias del backend dentro del proyecto. Por esta razón, los comandos de Python utilizan el ejecutable de `backend/.venv`.

## Preparación de la base de datos

PostgreSQL debe estar disponible en `127.0.0.1`, puerto `5432`. Desde la carpeta principal ejecutamos:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\preparar_base_local.py
.\backend\.venv\Scripts\python.exe .\backend\scripts\aplicar_modelo_fisico.py
.\backend\.venv\Scripts\python.exe .\backend\scripts\cargar_demo.py
```

Cada comando tiene una función:

1. **Preparar la base local:** solicita la contraseña del usuario administrador `postgres`, crea el usuario de la aplicación y la base `autos_colombia`, y guarda la configuración de conexión.
2. **Aplicar el modelo físico:** ejecuta las migraciones y comprueba que estén creadas las ocho tablas del proyecto con la revisión `0003`.
3. **Cargar la demostración:** agrega los datos ficticios que vamos a utilizar para probar la aplicación.

La configuración de conexión se guarda en `backend/.env`. Este archivo es privado y está excluido de Git. Al instalar el proyecto en otro equipo, cada persona utiliza su propia contraseña de PostgreSQL; no necesita la contraseña del equipo donde se desarrolló.

Si ya existe una configuración propia, debemos revisarla antes de ejecutar el preparador. Las migraciones comprueban la estructura existente y detienen el proceso si encuentran tablas ajenas al proyecto o vehículos anteriores que aún no estén asociados a un cliente.

## Cómo iniciamos la aplicación

Abrimos **dos terminales**, cada una ubicada inicialmente en la carpeta principal del repositorio.

En la primera iniciamos la API del backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

En la segunda iniciamos la interfaz de Angular:

```powershell
cd frontend
npm.cmd start -- --host 127.0.0.1 --port 4200
```

Con ambos servicios iniciados, ingresamos a [Autos Colombia](http://127.0.0.1:4200/control-acceso).

Angular se comunica con la API mediante el proxy configurado en el proyecto. Si actualizamos el código o la configuración del proxy, reiniciamos los servicios para cargar los cambios. Para detenerlos utilizamos `Ctrl+C` en cada terminal.

También podemos consultar:

- [Estado de la API](http://127.0.0.1:8000/health): permite comprobar que el backend responde. Esta consulta no depende de la conexión con PostgreSQL.
- [Documentación de la API](http://127.0.0.1:8000/docs): muestra las rutas y los datos que recibe y devuelve cada operación.

## Datos para probar la aplicación

La demostración prepara 70 celdas para automóviles y camionetas, identificadas de A01 a A70, y 10 para motos, de M01 a M10. También agrega a la operadora Ana López y los siguientes vehículos:

| Placa | Tipo | Mensualidad al cargar por primera vez | Documento ficticio del cliente |
|---|---|---|---|
| ABC123 | Automóvil | Vigente | DEMO-001 |
| DEF456 | Camioneta | Vigente | DEMO-002 |
| JKL45F | Moto | Vigente | DEMO-003 |
| GHI78F | Moto | Vencida | DEMO-004 |

Los nombres y documentos son ficticios. Las vigencias se calculan tomando como referencia el momento de la primera carga, para permitir la prueba en otro equipo.

Podemos ejecutar nuevamente la carga de demostración: solo agrega los registros que hacen falta. Las estancias realizadas se conservan y las mensualidades existentes no se renuevan automáticamente.

## Recorrido de prueba

1. **Registrar una entrada.** Consultamos la placa ABC123 y confirmamos el ingreso. El sistema asigna una celda libre y compatible, registra la fecha y hora y genera el comprobante. Su número corresponde al identificador de la estancia.
2. **Revisar el comprobante y el ingreso duplicado.** Podemos imprimirlo o guardarlo como PDF. Si intentamos ingresar nuevamente el mismo vehículo, el sistema debe informar que ya tiene una estancia abierta.
3. **Comprobar las validaciones.** Consultamos GHI78F para verificar el rechazo por mensualidad vencida. Una placa que no esté registrada también debe generar un mensaje de rechazo.
4. **Corregir una celda.** En «Registrar salida / corregir», consultamos ABC123, desplegamos la corrección, elegimos otra celda disponible y compatible e indicamos el motivo. Al reimprimir el comprobante se mantienen el número de estancia y la hora de ingreso, con la celda actualizada.
5. **Registrar la salida.** Consultamos nuevamente ABC123 e ingresamos el número del comprobante presentado. Un número incorrecto debe impedir el cierre. Al confirmar con el número correcto, se registra la salida y se libera la celda.
6. **Probar la pérdida del comprobante.** Ingresamos JKL45F y luego consultamos su salida. Marcamos la pérdida, verificamos presencialmente el nombre y documento del cliente asociado, escribimos DEMO-003 y el motivo, y confirmamos la verificación. Un documento diferente debe impedir la salida.
7. **Consultar la operación.** Revisamos «Vehículos presentes» e «Historial». Podemos filtrar por placa exacta y por fechas de entrada. El historial incluye estancias abiertas y cerradas y muestra 20 registros por página.

## Reglas de la operación

La mensualidad corresponde a cada vehículo e inicia desde el momento de su compra. Por ejemplo, si comienza el 21 de octubre a las 10:00, vence el 21 de noviembre a las 10:00. Cuando el mes siguiente no tiene el mismo día, se utiliza su último día. El inicio está incluido en la vigencia; al llegar a la hora de vencimiento, ya no se permite un nuevo ingreso.

Si la mensualidad vence mientras el vehículo está dentro, esto no impide registrar su salida.

También tenemos en cuenta las siguientes reglas:

- Un vehículo solo puede tener una estancia abierta y una celda solo puede estar ocupada por una estancia a la vez. PostgreSQL respalda estas condiciones con índices únicos.
- La celda de ingreso se asigna automáticamente según el tipo de vehículo y la disponibilidad. Se utilizan bloqueos de fila para coordinar operaciones simultáneas y se intenta otra celda si aparece un conflicto de ocupación.
- La salida requiere el comprobante de la estancia abierta. En caso de pérdida, se registra una incidencia con el motivo, la coincidencia del documento y la confirmación de la verificación presencial de identidad.
- La corrección de celda y su registro se realizan dentro de una misma transacción. Se conserva el número de estancia y la fecha y hora de entrada.
- El resumen diferencia los vehículos inscritos de los presentes y muestra las celdas libres por tipo.
- La reimpresión no crea otra estancia. Las fechas y horas de operación las asigna el servidor y se muestran en la zona horaria `America/Bogota`.

La selección del operador permite identificar quién realizó cada operación. En esta entrega no se implementa autenticación ni administración completa de usuarios.

## Verificación del funcionamiento

Desde la carpeta principal podemos ejecutar una verificación del flujo contra PostgreSQL:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\verificar_ea1.py
```

Esta comprobación utiliza registros temporales para revisar entrada, mensualidad, duplicados, corrección, reimpresión, salida con comprobante, pérdida, documento incorrecto, historial y salida después del vencimiento de la mensualidad.

Al finalizar revierte sus registros temporales y conserva los datos existentes. Las secuencias de identificadores pueden avanzar, por lo que no es necesario que los números de comprobante sean consecutivos.

Para ejecutar las pruebas unitarias y de contratos, abrimos una terminal desde la carpeta principal y ejecutamos:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas heredadas que se habilitan con `RUN_POSTGRES_TESTS=1` corresponden a las revisiones anteriores del esquema. No debemos habilitarlas sobre la revisión `0003`; para comprobar esta revisión con PostgreSQL utilizamos `verificar_ea1.py`. Las pruebas unitarias y HTTP complementan la verificación con la base de datos.

Para compilar y probar Angular, utilizamos otra terminal desde la carpeta principal:

```powershell
cd frontend
npm.cmd run build
npm.cmd test -- --watch=false
```

## Organización del repositorio

El repositorio contiene el código, las migraciones, las pruebas, los scripts y las instrucciones necesarias para ejecutar la aplicación. Las rutas `/operacion/*` corresponden a los servicios de esta EA1.

Los módulos de catálogo del repositorio inicial se conservan como base para las siguientes iteraciones. Las antiguas rutas `/estancias/*` ya no se publican, porque permitían registrar operaciones sin todas las validaciones definidas para esta entrega.

Las credenciales, el entorno virtual, `node_modules` y las compilaciones quedan excluidos de Git. Los diagramas, mockups y demás entregables académicos se presentan en el documento de la EA1.
