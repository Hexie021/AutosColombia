"""Modelos iniciales. Importar este módulo no crea tablas ni abre conexiones."""

from calendar import monthrange
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import Boolean, BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index, Integer, Text, UniqueConstraint, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates


class Base(DeclarativeBase):
    pass


def required_text(value: str, attribute: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{attribute} debe ser texto no vacío.")
    return value.strip()


class Cliente(Base):
    __tablename__ = "cliente"
    __table_args__ = (
        UniqueConstraint("documento", name="uq_cliente_documento"),
        CheckConstraint("nombre ~ '[^[:space:]]'", name="ck_cliente_nombre_no_vacio"),
        CheckConstraint("documento ~ '[^[:space:]]'", name="ck_cliente_documento_no_vacio"),
        CheckConstraint("documento = btrim(documento)", name="ck_cliente_documento_normalizado"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    documento: Mapped[str] = mapped_column(Text, nullable=False)

    @validates("nombre", "documento")
    def validate_text(self, key: str, value: str) -> str:
        return required_text(value, key)


class Vehiculo(Base):
    __tablename__ = "vehiculo"
    __table_args__ = (
        UniqueConstraint("placa", name="uq_vehiculo_placa"),
        CheckConstraint("placa ~ '[^[:space:]]'", name="ck_vehiculo_placa_no_vacia"),
        CheckConstraint("placa = upper(regexp_replace(placa, '^[[:space:]]+|[[:space:]]+$', '', 'g'))", name="ck_vehiculo_placa_normalizada"),
        CheckConstraint("color ~ '[^[:space:]]'", name="ck_vehiculo_color_no_vacio"),
        CheckConstraint("marca ~ '[^[:space:]]'", name="ck_vehiculo_marca_no_vacia"),
        CheckConstraint("modelo BETWEEN 1 AND 9999", name="ck_vehiculo_modelo_anio"),
        CheckConstraint("tipo IN ('MOTO', 'AUTOMOVIL', 'CAMIONETA')", name="ck_vehiculo_tipo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id", name="fk_vehiculo_cliente", ondelete="RESTRICT"), nullable=False
    )
    cliente: Mapped[Cliente] = relationship()
    placa: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(Text, nullable=False)
    modelo: Mapped[int] = mapped_column(Integer, nullable=False)
    marca: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)

    @validates("placa", "color", "marca", "tipo")
    def validate_text(self, key: str, value: str) -> str:
        value = required_text(value, key)
        if key == "placa":
            return value.upper()
        if key == "tipo" and value not in {"MOTO", "AUTOMOVIL", "CAMIONETA"}:
            raise ValueError("tipo debe ser MOTO, AUTOMOVIL o CAMIONETA.")
        return value

    @validates("modelo")
    def validate_modelo(self, key: str, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 9999:
            raise ValueError("modelo debe ser un año entero entre 1 y 9999.")
        return value


class Celda(Base):
    __tablename__ = "celda"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_celda_codigo"),
        CheckConstraint("codigo ~ '[^[:space:]]'", name="ck_celda_codigo_no_vacio"),
        CheckConstraint("codigo = upper(regexp_replace(codigo, '^[[:space:]]+|[[:space:]]+$', '', 'g'))", name="ck_celda_codigo_normalizado"),
        CheckConstraint("tipo ~ '[^[:space:]]'", name="ck_celda_tipo_no_vacio"),
        CheckConstraint("tipo IN ('MOTO', 'AUTOMOVIL_CAMIONETA')", name="ck_celda_tipo_admitido"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)

    @validates("codigo", "tipo")
    def validate_text(self, key: str, value: str) -> str:
        value = required_text(value, key)
        return value.upper() if key == "codigo" else value

    def es_compatible(self, tipo_vehiculo: str) -> bool:
        return ((self.tipo == "MOTO" and tipo_vehiculo == "MOTO") or
                (self.tipo == "AUTOMOVIL_CAMIONETA" and tipo_vehiculo in {"AUTOMOVIL", "CAMIONETA"}))


class Operador(Base):
    __tablename__ = "operador"
    __table_args__ = (
        CheckConstraint("nombre ~ '[^[:space:]]'", name="ck_operador_nombre_no_vacio"),
        CheckConstraint("telefono ~ '[^[:space:]]'", name="ck_operador_telefono_no_vacio"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    telefono: Mapped[str] = mapped_column(Text, nullable=False)

    @validates("nombre", "telefono")
    def validate_text(self, key: str, value: str) -> str:
        return required_text(value, key)


class Estancia(Base):
    __tablename__ = "estancia"
    __table_args__ = (
        CheckConstraint("salida >= entrada", name="ck_estancia_orden_fechas"),
        CheckConstraint(
            "(salida IS NULL) = (operador_salida_id IS NULL)",
            name="ck_estancia_cierre_completo",
        ),
        Index("uq_estancia_vehiculo_abierta", "vehiculo_id", unique=True,
              postgresql_where=text("salida IS NULL")),
        Index("uq_estancia_celda_abierta", "celda_id", unique=True,
              postgresql_where=text("salida IS NULL")),
        Index("ix_estancia_vehiculo_entrada", "vehiculo_id", "entrada"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehiculo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vehiculo.id", name="fk_estancia_vehiculo", ondelete="RESTRICT"), nullable=False
    )
    celda_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("celda.id", name="fk_estancia_celda", ondelete="RESTRICT"), nullable=False
    )
    entrada: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    salida: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operador_entrada_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("operador.id", name="fk_estancia_operador_entrada", ondelete="RESTRICT"), nullable=False
    )
    operador_salida_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("operador.id", name="fk_estancia_operador_salida", ondelete="RESTRICT"), nullable=True
    )

    vehiculo: Mapped[Vehiculo] = relationship()
    celda: Mapped[Celda] = relationship()
    operador_entrada: Mapped[Operador] = relationship(foreign_keys=[operador_entrada_id])
    operador_salida: Mapped[Operador | None] = relationship(foreign_keys=[operador_salida_id])

    def esta_abierta(self) -> bool:
        return self.salida is None

    def cerrar(self, fecha_salida: datetime, operador: Operador) -> None:
        """Valida y asigna el cierre; el servicio debe gestionar flush y commit."""
        if not self.esta_abierta():
            raise ValueError("La estancia ya está cerrada.")
        if not isinstance(fecha_salida, datetime) or fecha_salida.utcoffset() is None:
            raise ValueError("La fecha de salida debe tener zona horaria.")
        if not isinstance(self.entrada, datetime) or self.entrada.utcoffset() is None:
            raise ValueError("La entrada debe estar cargada y tener zona horaria antes de cerrar.")
        if fecha_salida.astimezone(timezone.utc) < self.entrada.astimezone(timezone.utc):
            raise ValueError("La salida no puede ser anterior a la entrada.")
        if not isinstance(operador, Operador) or operador.id is None:
            raise ValueError("El operador de salida debe tener un id asignado.")
        self.salida = fecha_salida
        self.operador_salida = operador
        self.operador_salida_id = operador.id



def fecha_con_zona(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("La fecha debe incluir zona horaria.")
    return value


def siguiente_mes(inicio: datetime) -> datetime:
    """Un mes calendario, preservando la hora de Bogotá y ajustando el día."""
    local = fecha_con_zona(inicio).astimezone(ZoneInfo("America/Bogota"))
    year = local.year + (local.month == 12)
    month = local.month % 12 + 1
    day = min(local.day, monthrange(year, month)[1])
    return local.replace(year=year, month=month, day=day)


class VigenciaMensualidad(Base):
    __tablename__ = "vigencia_mensualidad"
    __table_args__ = (
        CheckConstraint("vencimiento > inicio", name="ck_vigencia_orden_fechas"),
        Index("ix_vigencia_vehiculo_fechas", "vehiculo_id", "inicio", "vencimiento"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehiculo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vehiculo.id", name="fk_vigencia_vehiculo", ondelete="RESTRICT"), nullable=False
    )
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vencimiento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vehiculo: Mapped[Vehiculo] = relationship()

    @validates("inicio", "vencimiento")
    def validar_fecha(self, key: str, value: datetime) -> datetime:
        return fecha_con_zona(value)

    def esta_vigente(self, fecha: datetime) -> bool:
        return self.inicio <= fecha_con_zona(fecha) < self.vencimiento


class CorreccionCelda(Base):
    __tablename__ = "correccion_celda"
    __table_args__ = (
        CheckConstraint("celda_anterior_id <> celda_nueva_id", name="ck_correccion_celdas_distintas"),
        CheckConstraint("motivo ~ '[^[:space:]]'", name="ck_correccion_motivo_no_vacio"),
        Index("ix_correccion_estancia_fecha", "estancia_id", "fecha"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    estancia_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("estancia.id", name="fk_correccion_estancia", ondelete="RESTRICT"), nullable=False
    )
    celda_anterior_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("celda.id", name="fk_correccion_celda_anterior", ondelete="RESTRICT"), nullable=False
    )
    celda_nueva_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("celda.id", name="fk_correccion_celda_nueva", ondelete="RESTRICT"), nullable=False
    )
    operador_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("operador.id", name="fk_correccion_operador", ondelete="RESTRICT"), nullable=False
    )
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    estancia: Mapped[Estancia] = relationship()
    celda_anterior: Mapped[Celda] = relationship(foreign_keys=[celda_anterior_id])
    celda_nueva: Mapped[Celda] = relationship(foreign_keys=[celda_nueva_id])
    operador: Mapped[Operador] = relationship()

    @validates("motivo")
    def validar_motivo(self, key: str, value: str) -> str:
        return required_text(value, key)


class IncidenciaSalida(Base):
    __tablename__ = "incidencia_salida"
    __table_args__ = (
        UniqueConstraint("estancia_id", name="uq_incidencia_estancia"),
        CheckConstraint("motivo ~ '[^[:space:]]'", name="ck_incidencia_motivo_no_vacio"),
        CheckConstraint("identidad_verificada IS TRUE", name="ck_incidencia_identidad_verificada"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    estancia_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("estancia.id", name="fk_incidencia_estancia", ondelete="RESTRICT"), nullable=False
    )
    operador_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("operador.id", name="fk_incidencia_operador", ondelete="RESTRICT"), nullable=False
    )
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    identidad_verificada: Mapped[bool] = mapped_column(Boolean, nullable=False)
    estancia: Mapped[Estancia] = relationship()
    operador: Mapped[Operador] = relationship()

    @validates("motivo")
    def validar_motivo(self, key: str, value: str) -> str:
        return required_text(value, key)
