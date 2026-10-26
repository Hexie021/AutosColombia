BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE vehiculo (
    id BIGINT GENERATED ALWAYS AS IDENTITY, 
    placa TEXT NOT NULL, 
    color TEXT NOT NULL, 
    modelo INTEGER NOT NULL, 
    marca TEXT NOT NULL, 
    tipo TEXT NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_vehiculo_placa UNIQUE (placa), 
    CONSTRAINT ck_vehiculo_placa_no_vacia CHECK (placa ~ '[^[:space:]]'), 
    CONSTRAINT ck_vehiculo_placa_normalizada CHECK (placa = upper(regexp_replace(placa, '^[[:space:]]+|[[:space:]]+$', '', 'g'))), 
    CONSTRAINT ck_vehiculo_color_no_vacio CHECK (color ~ '[^[:space:]]'), 
    CONSTRAINT ck_vehiculo_marca_no_vacia CHECK (marca ~ '[^[:space:]]'), 
    CONSTRAINT ck_vehiculo_modelo_anio CHECK (modelo BETWEEN 1 AND 9999), 
    CONSTRAINT ck_vehiculo_tipo CHECK (tipo IN ('MOTO', 'AUTOMOVIL', 'CAMIONETA'))
);

CREATE TABLE celda (
    id BIGINT GENERATED ALWAYS AS IDENTITY, 
    codigo TEXT NOT NULL, 
    tipo TEXT NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_celda_codigo UNIQUE (codigo), 
    CONSTRAINT ck_celda_codigo_no_vacio CHECK (codigo ~ '[^[:space:]]'), 
    CONSTRAINT ck_celda_codigo_normalizado CHECK (codigo = upper(regexp_replace(codigo, '^[[:space:]]+|[[:space:]]+$', '', 'g'))), 
    CONSTRAINT ck_celda_tipo_no_vacio CHECK (tipo ~ '[^[:space:]]')
);

CREATE TABLE operador (
    id BIGINT GENERATED ALWAYS AS IDENTITY, 
    nombre TEXT NOT NULL, 
    telefono TEXT NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_operador_nombre_no_vacio CHECK (nombre ~ '[^[:space:]]'), 
    CONSTRAINT ck_operador_telefono_no_vacio CHECK (telefono ~ '[^[:space:]]')
);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

-- Running upgrade 0001 -> 0002

CREATE TABLE estancia (
    id BIGINT GENERATED ALWAYS AS IDENTITY, 
    vehiculo_id BIGINT NOT NULL, 
    celda_id BIGINT NOT NULL, 
    entrada TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    salida TIMESTAMP WITH TIME ZONE, 
    operador_entrada_id BIGINT NOT NULL, 
    operador_salida_id BIGINT, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_estancia_vehiculo FOREIGN KEY(vehiculo_id) REFERENCES vehiculo (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_estancia_celda FOREIGN KEY(celda_id) REFERENCES celda (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_estancia_operador_entrada FOREIGN KEY(operador_entrada_id) REFERENCES operador (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_estancia_operador_salida FOREIGN KEY(operador_salida_id) REFERENCES operador (id) ON DELETE RESTRICT, 
    CONSTRAINT ck_estancia_orden_fechas CHECK (salida >= entrada), 
    CONSTRAINT ck_estancia_cierre_completo CHECK ((salida IS NULL) = (operador_salida_id IS NULL))
);

CREATE UNIQUE INDEX uq_estancia_vehiculo_abierta ON estancia (vehiculo_id) WHERE salida IS NULL;

CREATE UNIQUE INDEX uq_estancia_celda_abierta ON estancia (celda_id) WHERE salida IS NULL;

CREATE INDEX ix_estancia_vehiculo_entrada ON estancia (vehiculo_id, entrada);

UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';

-- Running upgrade 0002 -> 0003

DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM vehiculo) THEN
            RAISE EXCEPTION 'Antes de migrar, debe planificarse la asociación de los vehículos existentes con sus clientes. No se modificaron sus datos.';
        END IF;
        IF EXISTS (SELECT 1 FROM celda WHERE tipo NOT IN ('MOTO', 'AUTOMOVIL_CAMIONETA')) THEN
            RAISE EXCEPTION 'Hay tipos de celda pendientes de clasificar. No se modificaron sus datos.';
        END IF;
    END $$;;

CREATE TABLE cliente (
    id BIGINT GENERATED ALWAYS AS IDENTITY, 
    nombre TEXT NOT NULL, 
    documento TEXT NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_cliente_documento UNIQUE (documento), 
    CONSTRAINT ck_cliente_nombre_no_vacio CHECK (nombre ~ '[^[:space:]]'), 
    CONSTRAINT ck_cliente_documento_no_vacio CHECK (documento ~ '[^[:space:]]'), 
    CONSTRAINT ck_cliente_documento_normalizado CHECK (documento = btrim(documento))
);

ALTER TABLE vehiculo ADD COLUMN cliente_id BIGINT NOT NULL;

ALTER TABLE vehiculo ADD CONSTRAINT fk_vehiculo_cliente FOREIGN KEY(cliente_id) REFERENCES cliente (id) ON DELETE RESTRICT;

ALTER TABLE celda ADD CONSTRAINT ck_celda_tipo_admitido CHECK (tipo IN ('MOTO', 'AUTOMOVIL_CAMIONETA'));

CREATE TABLE vigencia_mensualidad (
    id BIGINT GENERATED ALWAYS AS IDENTITY, 
    vehiculo_id BIGINT NOT NULL, 
    inicio TIMESTAMP WITH TIME ZONE NOT NULL, 
    vencimiento TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_vigencia_vehiculo FOREIGN KEY(vehiculo_id) REFERENCES vehiculo (id) ON DELETE RESTRICT, 
    CONSTRAINT ck_vigencia_orden_fechas CHECK (vencimiento > inicio)
);

CREATE INDEX ix_vigencia_vehiculo_fechas ON vigencia_mensualidad (vehiculo_id, inicio, vencimiento);

CREATE TABLE correccion_celda (
    id BIGINT GENERATED ALWAYS AS IDENTITY, 
    estancia_id BIGINT NOT NULL, 
    celda_anterior_id BIGINT NOT NULL, 
    celda_nueva_id BIGINT NOT NULL, 
    operador_id BIGINT NOT NULL, 
    fecha TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    motivo TEXT NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_correccion_estancia FOREIGN KEY(estancia_id) REFERENCES estancia (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_correccion_celda_anterior FOREIGN KEY(celda_anterior_id) REFERENCES celda (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_correccion_celda_nueva FOREIGN KEY(celda_nueva_id) REFERENCES celda (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_correccion_operador FOREIGN KEY(operador_id) REFERENCES operador (id) ON DELETE RESTRICT, 
    CONSTRAINT ck_correccion_celdas_distintas CHECK (celda_anterior_id <> celda_nueva_id), 
    CONSTRAINT ck_correccion_motivo_no_vacio CHECK (motivo ~ '[^[:space:]]')
);

CREATE INDEX ix_correccion_estancia_fecha ON correccion_celda (estancia_id, fecha);

CREATE TABLE incidencia_salida (
    id BIGINT GENERATED ALWAYS AS IDENTITY, 
    estancia_id BIGINT NOT NULL, 
    operador_id BIGINT NOT NULL, 
    fecha TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    motivo TEXT NOT NULL, 
    identidad_verificada BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_incidencia_estancia FOREIGN KEY(estancia_id) REFERENCES estancia (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_incidencia_operador FOREIGN KEY(operador_id) REFERENCES operador (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_incidencia_estancia UNIQUE (estancia_id), 
    CONSTRAINT ck_incidencia_motivo_no_vacio CHECK (motivo ~ '[^[:space:]]'), 
    CONSTRAINT ck_incidencia_identidad_verificada CHECK (identidad_verificada IS TRUE)
);

UPDATE alembic_version SET version_num='0003' WHERE alembic_version.version_num = '0002';

COMMIT;

