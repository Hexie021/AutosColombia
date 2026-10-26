import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { finalize, timeout } from 'rxjs';
import { API_BASE_URL } from '../services/api.service';

interface EstanciaEA1 {
  id: number;
  placa: string;
  tipo: string;
  cliente: string;
  celda: string;
  celda_id: number;
  entrada: string;
  salida: string | null;
  operador_entrada: string;
  operador_salida: string | null;
}
interface EstadoEA1 {
  placa: string;
  marca: string;
  modelo: number;
  color: string;
  tipo: string;
  cliente: string;
  vigencia: { inicio: string; vencimiento: string } | null;
  estancia: EstanciaEA1 | null;
}
interface Catalogos {
  operadores: { id: number; nombre: string }[];
  celdas: { id: number; codigo: string; tipo: string; ocupada: boolean }[];
  resumen: {
    presentes: number;
    libres: number;
    inscritos: number;
    motos_libres: number;
    autos_libres: number;
  };
}
interface Listado {
  items: EstanciaEA1[];
  total: number;
  offset: number;
  limit: number;
}

@Component({
  selector: 'app-control-acceso',
  imports: [FormsModule],
  templateUrl: './control-acceso.html',
  styleUrl: './control-acceso.css',
})
export class ControlAcceso {
  private readonly http = inject(HttpClient);
  private readonly destroy = inject(DestroyRef);
  private readonly base = `${inject(API_BASE_URL)}/operacion`;
  private version = 0;
  readonly catalogos = signal<Catalogos | null>(null);
  readonly estado = signal<EstadoEA1 | null>(null);
  readonly comprobante = signal<EstanciaEA1 | null>(null);
  readonly lista = signal<Listado>({ items: [], total: 0, offset: 0, limit: 20 });
  readonly busy = signal(false);
  readonly mensaje = signal('');
  readonly error = signal('');
  readonly tab = signal('entrada');
  placa = '';
  operador: number | null = null;
  numero: number | null = null;
  perdido = false;
  documento = '';
  motivo = '';
  verificada = false;
  nuevaCelda: number | null = null;
  motivoCorreccion = '';
  filtroPlaca = '';
  desde = '';
  hasta = '';

  constructor() {
    this.cargar();
  }

  cargar(): void {
    this.http
      .get<Catalogos>(`${this.base}/catalogos`)
      .pipe(timeout(15000), takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.catalogos.set(data);
          if (!this.operador) this.operador = data.operadores[0]?.id ?? null;
        },
        error: (e) => this.error.set(this.detalle(e)),
      });
  }
  cambiarTab(value: string): void {
    if (this.busy()) return;
    this.tab.set(value);
    this.error.set('');
    this.mensaje.set('');
    if (value === 'presentes' || value === 'historial') this.listar(0);
  }
  cambiarPlaca(value: string): void {
    this.placa = value;
    this.version++;
    this.estado.set(null);
    this.numero = null;
    this.perdido = false;
    this.documento = '';
    this.motivo = '';
    this.verificada = false;
  }
  buscar(): void {
    if (this.busy() || !this.placa.trim()) return;
    this.placa = this.placa.trim().toUpperCase();
    const version = ++this.version;
    this.estado.set(null);
    this.error.set('');
    this.mensaje.set('');
    this.busy.set(true);
    this.http
      .get<EstadoEA1>(`${this.base}/vehiculo/${encodeURIComponent(this.placa)}`)
      .pipe(
        timeout(15000),
        finalize(() => this.busy.set(false)),
        takeUntilDestroyed(this.destroy),
      )
      .subscribe({
        next: (data) => {
          if (version === this.version) this.estado.set(data);
        },
        error: (e) => {
          if (version === this.version) this.error.set(this.detalle(e));
        },
      });
  }
  registrarEntrada(): void {
    const state = this.estado();
    if (!state || state.estancia || !state.vigencia) return;
    this.operar('entrada', { placa: state.placa, operador_id: this.operador });
  }
  registrarSalida(): void {
    const state = this.estado();
    if (!state?.estancia) return;
    if (this.perdido && (!this.verificada || !this.documento.trim() || !this.motivo.trim())) {
      this.error.set('Verifica presencialmente la identidad y completa documento y motivo.');
      return;
    }
    if (!this.perdido && (!this.numero || this.numero < 1)) {
      this.error.set('Escribe el número del comprobante presentado.');
      return;
    }
    this.operar('salida', {
      placa: state.placa,
      operador_id: this.operador,
      comprobante_id: this.perdido ? null : this.numero,
      perdido: this.perdido,
      documento: this.documento,
      motivo: this.motivo,
      identidad_verificada: this.verificada,
    });
  }
  corregir(): void {
    const stay = this.estado()?.estancia;
    if (!stay || !this.nuevaCelda || !this.motivoCorreccion.trim()) {
      this.error.set('Selecciona una celda y escribe el motivo de la corrección.');
      return;
    }
    this.operar('correccion', {
      estancia_id: stay.id,
      celda_id: this.nuevaCelda,
      operador_id: this.operador,
      motivo: this.motivoCorreccion.trim(),
    });
  }
  private operar(accion: string, body: object): void {
    if (this.busy() || !this.operador) return;
    this.busy.set(true);
    this.error.set('');
    this.mensaje.set('');
    this.http
      .post<EstanciaEA1>(`${this.base}/${accion}`, body)
      .pipe(
        timeout(15000),
        finalize(() => this.busy.set(false)),
        takeUntilDestroyed(this.destroy),
      )
      .subscribe({
        next: (data) => {
          this.comprobante.set(data);
          this.estado.set(null);
          this.version++;
          this.mensaje.set(
            accion === 'entrada'
              ? `Entrada registrada. Celda ${data.celda}.`
              : accion === 'salida'
                ? `Salida registrada. Celda ${data.celda} liberada.`
                : 'Celda corregida. Se conserva la estancia y la hora de ingreso.',
          );
          this.numero = null;
          this.perdido = false;
          this.verificada = false;
          this.documento = '';
          this.motivo = '';
          this.nuevaCelda = null;
          this.motivoCorreccion = '';
          this.cargar();
        },
        error: (e) => {
          this.estado.set(null);
          this.version++;
          this.error.set(this.detalle(e) + ' Consulta nuevamente antes de reintentar.');
          this.cargar();
        },
      });
  }
  listar(offset = 0): void {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set('');
    let params = new HttpParams()
      .set('presentes', this.tab() === 'presentes')
      .set('offset', offset)
      .set('limit', 20);
    if (this.filtroPlaca.trim())
      params = params.set('placa', this.filtroPlaca.trim().toUpperCase());
    if (this.desde) params = params.set('desde', this.desde);
    if (this.hasta) params = params.set('hasta', this.hasta);
    this.http
      .get<Listado>(`${this.base}/estancias`, { params })
      .pipe(
        timeout(15000),
        finalize(() => this.busy.set(false)),
        takeUntilDestroyed(this.destroy),
      )
      .subscribe({
        next: (data) => {
          this.lista.set(data);
          this.cargar();
        },
        error: (e) => {
          this.lista.set({ items: [], total: 0, offset: 0, limit: 20 });
          this.error.set(this.detalle(e));
        },
      });
  }
  reimprimir(id: number): void {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set('');
    this.http
      .get<EstanciaEA1>(`${this.base}/comprobante/${id}`)
      .pipe(
        timeout(15000),
        finalize(() => this.busy.set(false)),
        takeUntilDestroyed(this.destroy),
      )
      .subscribe({
        next: (data) => this.comprobante.set(data),
        error: (e) => this.error.set(this.detalle(e)),
      });
  }
  compatibles() {
    const state = this.estado();
    const tipo = state?.tipo === 'MOTO' ? 'MOTO' : 'AUTOMOVIL_CAMIONETA';
    return this.catalogos()?.celdas.filter((c) => !c.ocupada && c.tipo === tipo) ?? [];
  }
  fecha(value: string | null): string {
    if (!value) return '—';
    return new Intl.DateTimeFormat('es-CO', {
      timeZone: 'America/Bogota',
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  }
  imprimir(): void {
    window.print();
  }
  private detalle(e: HttpErrorResponse): string {
    if (typeof e.error?.detail === 'string') return e.error.detail;
    if (e.status === 422) return 'Revisa los datos, el comprobante y las fechas ingresadas.';
    return 'No se pudo completar la solicitud. Comprueba que la API esté iniciada y consulta el estado antes de reintentar.';
  }
}
