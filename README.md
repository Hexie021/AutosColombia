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
Set-Location -LiteralPath 'C:\Users\user\Documents\IU DIGITAL\Clase Ingeniería de Software\AutosColombia\backend'
.\.venv\Scripts\python.exe check_db.py
.\.venv\Scripts\python.exe -m alembic -c alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c alembic.ini heads
.\.venv\Scripts\python.exe -m alembic -c alembic.ini history
.\.venv\Scripts\python.exe -m pytest tests/test_estancia.py -q
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade 0002
if ($LASTEXITCODE -ne 0) { throw 'La migración falló; detener y revisar.' }
.\.venv\Scripts\python.exe -m alembic -c alembic.ini current
```

`upgrade 0002` terminó con código 0; la consulta posterior mostró `0002 (head)`.
Las consultas de catálogo con SQLAlchemy comprobaron:

| Elemento | Resultado observado |
| --- | --- |
| Tabla y columnas | `estancia` existe con las siete columnas acordadas, sin campos adicionales. |
| Identificador | BIGINT, identidad ALWAYS, clave primaria `id`. |
| Nulabilidad | Solo `salida` y `operador_salida_id` admiten NULL. |
| Fechas | Ambas con zona horaria; entrada DEFAULT now(), salida sin valor predeterminado. |
| Referencias | Cuatro FK hacia vehiculo, celda y los dos operadores, todas ON DELETE RESTRICT. |
| Fechas válidas | CHECK `salida >= entrada`. |
| Cierre completo | CHECK `(salida IS NULL) = (operador_salida_id IS NULL)`. |
| Exclusividad de abiertas | Dos índices únicos, sobre vehiculo_id y celda_id, ambos WHERE salida IS NULL. |
| Historial | Índice no único `(vehiculo_id, entrada)`, en ese orden. |
| Estado del catálogo | Restricciones validadas; todos los índices válidos y listos. |

Se conservaron vehiculo, celda y operador. No se borraron ni recrearon tablas
existentes. En esta etapa solo se modificó este README en el código del proyecto;
el cambio de PostgreSQL fue la aplicación de la revisión existente `0002`.

**Pendiente:** pruebas de inserciones inválidas, bloqueos de eliminación y
concurrencia con datos de prueba, y ensayo de downgrade en una base aislada.
La inspección del catálogo confirma las definiciones instaladas; no equivale
a ejecutar esos escenarios. No se repitió la suite completa ni se implementaron
servicios, endpoints o Angular. No se creó un commit.

`Estancia` se encuentra en `backend/app/models.py`, junto a los modelos existentes:

- `id`: BIGINT GENERATED ALWAYS AS IDENTITY, clave primaria.
- `vehiculo_id`, `celda_id`, `operador_entrada_id`: BIGINT obligatorios con FK.
- `entrada`: fecha/hora con zona horaria, obligatoria, DEFAULT now() del servidor.
- `salida`: fecha/hora con zona horaria nullable; inicialmente NULL.
- `operador_salida_id`: BIGINT nullable, FK al operador de salida.

Las relaciones `vehiculo`, `celda`, `operador_entrada` y `operador_salida` permiten
navegar desde una estancia. Las dos relaciones de operador usan explícitamente
sus respectivas claves foráneas. Las cuatro FK tienen ON DELETE RESTRICT y no
hay cascadas ORM de eliminación: los registros referenciados no se pueden borrar
mientras exista historial, incluso si la estancia está cerrada.

Los índices únicos parciales `uq_estancia_vehiculo_abierta` y
`uq_estancia_celda_abierta` usan `WHERE salida IS NULL`; impiden dos estancias
abiertas para el mismo vehículo o celda, sin restringir su historial cerrado.
`ix_estancia_vehiculo_entrada` indexa `(vehiculo_id, entrada)`. Los CHECK
`ck_estancia_orden_fechas` y `ck_estancia_cierre_completo` exigen salida >= entrada
y que salida/operador_salida_id estén ambos nulos o ambos informados.

`esta_abierta()` calcula `salida is None`. `cerrar(fecha_salida, operador)` recibe
un objeto Operador con id asignado, valida el estado abierto y fechas conscientes
de zona horaria, compara los instantes en UTC y asigna fecha, relación e id de
salida. Acepta salida igual a entrada. Si falla una validación no modifica el
cierre. No hace flush ni commit. Antes de cerrar una estancia nueva, el futuro
servicio deberá hacer flush y cargar la entrada generada por PostgreSQL; también
deberá persistir el operador si es nuevo. La FK verifica su existencia al guardar.
PostgreSQL conserva instantes con zona horaria, no el nombre original del huso.

### Revisar sin aplicar (PowerShell)

Usa el entorno virtual existente; no necesitas activarlo ni reinstalar paquetes:

```powershell
Set-Location -LiteralPath 'C:\Users\user\Documents\IU DIGITAL\Clase Ingeniería de Software\AutosColombia\backend'
.\.venv\Scripts\python.exe check_db.py
.\.venv\Scripts\python.exe -m alembic -c alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c alembic.ini heads
.\.venv\Scripts\python.exe -m alembic -c alembic.ini history
Get-Content -LiteralPath migrations\versions\0002_estancia.py
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade 0001:0002 --sql
.\.venv\Scripts\python.exe -m pytest tests/test_estancia.py -q
```

El rango `0001:0002 --sql` solo genera SQL de la nueva revisión, sin conexión ni
ejecución de DDL. Revisa una creación de tabla, cuatro FK RESTRICT, dos CHECK,
dos índices únicos parciales y el índice de historial. No debe recrear las tablas
existentes. No uses `stamp` para simular que la migración fue aplicada.

### Comando de aplicación (ya ejecutado en esta base)

El siguiente bloque **sí modifica el esquema** cuando la revisión está pendiente.
Se conserva como referencia para otros entornos; esta base ya está en `0002`.
Si la tabla existe pero Alembic indica `0001`, detente y revisa la discrepancia.

```powershell
Set-Location -LiteralPath 'C:\Users\user\Documents\IU DIGITAL\Clase Ingeniería de Software\AutosColombia\backend'
.\.venv\Scripts\python.exe check_db.py
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL no está disponible.' }
.\.venv\Scripts\python.exe -m alembic -c alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade 0002
if ($LASTEXITCODE -ne 0) { throw 'La migración falló; revisar el esquema.' }
.\.venv\Scripts\python.exe -m alembic -c alembic.ini current
```

Se obtuvo `0002 (head)`. El downgrade elimina la tabla y todo su historial;
no forma parte de estos comandos y no se ejecutó.

### Comprobar después tabla, relaciones e índices

Este bloque de PowerShell/Python realiza únicamente consultas de catálogo usando
la configuración existente, sin imprimir credenciales. En esta base ya debe
mostrar la estructura instalada; si falta la tabla, informa del problema.

```powershell
Set-Location -LiteralPath 'C:\Users\user\Documents\IU DIGITAL\Clase Ingeniería de Software\AutosColombia\backend'
@'
from sqlalchemy import inspect
from app.database import get_engine
try:
    with get_engine().connect() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("estancia"):
            print("La tabla estancia no existe; migracion 0002 pendiente.")
            raise SystemExit(1)
        for column in inspector.get_columns("estancia"):
            print(column["name"], column["type"], "nullable:", column["nullable"],
                  "default:", column.get("default"), "identity:", column.get("identity"))
        print("PK:", inspector.get_pk_constraint("estancia"))
        print("FK:", inspector.get_foreign_keys("estancia"))
        print("CHECK:", inspector.get_check_constraints("estancia"))
        print("Indices:", inspector.get_indexes("estancia"))
except Exception:
    print("No se pudo inspeccionar estancia; revisar conexion y permisos localmente.")
    raise SystemExit(1)
'@ | .\.venv\Scripts\python.exe -
```

Comprueba las siete columnas, PK id, cuatro FK con RESTRICT, dos CHECK y tres
índices descritos arriba. En los dos índices únicos revisa `unique=True` y
`postgresql_where` equivalente a `salida IS NULL`; en el índice de historial,
el orden de columnas debe ser vehiculo_id, entrada.

### Alcance y resultados de Estancia

- Modificados: `backend/app/models.py` y este README.
- Nueva migración: `backend/migrations/versions/0002_estancia.py`; `0001` intacta.
- Nuevas pruebas: `backend/tests/test_estancia.py` cubre cierre, zonas horarias,
  entradas no cargadas, operador sin id, cierre repetido, ausencia de mutación
  ante errores, relaciones sin cascada y equivalencia de SQL modelo/migración.
- Ajustadas: `backend/tests/test_models.py` limita la obligatoriedad de todos los
  campos a los tres modelos iniciales; las pruebas de integración de vehículos y
  operadores aceptan tanto `0001` como `0002`, para poder ejecutarlas antes y
  después de aplicar esta revisión.
- Comprobado: **96 pruebas aprobadas** con integración de los CRUD actuales y
  rollback; SQL offline revisado. Un aviso conocido de Starlette/httpx.
- La aplicación y la verificación de catálogo ya se completaron en la etapa
  documentada al principio. Quedan pendientes las pruebas de comportamiento en
  PostgreSQL aislado y la reversión; no se ha ejecutado downgrade.

No se añadieron servicios, esquemas API, controladores, endpoints ni cambios Angular.

## Pantalla de operadores en Angular

Disponible desde **Operadores** en la navegación y en
<http://127.0.0.1:4200/gestion/operadores>. Incluye listado de diez registros por
página, formulario reactivo de nombre y teléfono, edición, confirmación de
eliminación con nombre/teléfono/id, estados de carga y mensajes de resultado.

Los dos campos son obligatorios; se recortan espacios exteriores y se rechazan
textos vacíos o solo espacios. Teléfono usa un control de texto (`type="tel"`),
sin formato ni longitud máxima inventados: conserva prefijos y ceros iniciales.
Los nombres y teléfonos repetidos están permitidos por la API. Durante las
solicitudes se bloquean las acciones para evitar envíos duplicados. Guardar o
eliminar recarga el listado; una última página vacía vuelve a la anterior.

`OperadoresService` centraliza las llamadas y reutiliza `API_BASE_URL`. El proxy
añade `/operadores` y `/operadores/**` hacia `127.0.0.1:8000`; no se cambió CORS
ni ningún archivo del backend. Reinicia Angular para cargar cambios del proxy.

### Iniciar y verificar con PowerShell

Terminal 1, si FastAPI todavía no está iniciado (usa el entorno existente):

```powershell
Set-Location -LiteralPath 'C:\Users\user\Documents\IU DIGITAL\Clase Ingeniería de Software\AutosColombia\backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
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
