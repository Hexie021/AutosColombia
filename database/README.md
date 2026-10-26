# Modelo físico de la primera iteración

La revisión 0003 completa las ocho tablas del modelo relacional. Las revisiones
0001 y 0002 conservan la base del profe, no se reescriben ni se borran sus tablas.

## Aplicar al destino local preparado

Desde la raíz del repositorio, después de preparar la base y verificar la conexión:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\aplicar_modelo_fisico.py
```

El comando modifica el esquema de la base local autos_colombia. Usa el usuario de
aplicación y la configuración privada existente. Verifica el destino, aplica las
migraciones y comprueba las ocho tablas y la revisión 0003. No elimina datos ni
recrea estructuras existentes. Si detecta vehículos sin asociación de cliente o
celdas con tipos anteriores sin clasificar, se detiene para planificar su adaptación.

Las tablas son cliente, vehiculo, celda, operador, estancia, vigencia_mensualidad,
correccion_celda e incidencia_salida. Alembic mantiene además alembic_version para
el historial técnico de migraciones; no es una entidad del negocio.

## Estructura y reglas

- Identificadores BIGINT generados por identidad; claves foráneas con RESTRICT.
- Documento del cliente, placa y código de celda únicos.
- Fechas de operaciones y vigencias con zona horaria.
- Vigencias con vencimiento posterior al inicio.
- Estancias con cierre completo: fecha y operario de salida se completan juntos.
- Índices únicos parciales para una sola estancia abierta por vehículo y por celda.
- Correcciones con celdas distintas y motivo obligatorio.
- Una incidencia confirmada por estancia, motivo obligatorio e identidad verificada.

La disponibilidad, el límite operativo de 80 celdas, la vigencia al ingreso,
la coherencia de una corrección y la confirmación de una salida excepcional deben
completarse en los servicios y verificarse con pruebas de integración. La estructura
por sí sola no implementa todos los casos de uso.

## SQL de referencia

modelo_fisico_ea1.sql es el SQL generado de las migraciones completas. Permite
revisar tipos, relaciones, restricciones e índices sin incluir credenciales.
Para aplicar el esquema, usa el comando anterior; no ejecutes ambos procedimientos
como instalaciones separadas sobre la misma base.

## Estado de esta etapa

Se verificó la equivalencia de las migraciones con los ocho modelos SQLAlchemy
y las reglas de mes calendario, límites de vigencia y compatibilidad. Pasaron
74 pruebas de configuración, modelos y migraciones sin conexión. Esto no confirma
que la revisión se haya aplicado: la ejecución del comando y la consulta real de
la base deben verificarlo. La carga inicial y la adaptación de los contratos y
servicios del código heredado se desarrollan en la etapa siguiente.