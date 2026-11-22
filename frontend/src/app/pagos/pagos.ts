import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize, TimeoutError } from 'rxjs';
import {
  ComprobantePago, ConceptoPago, ConsultaPago, HistorialPago, PagosService, SolicitudPago,
} from '../services/pagos.service';

@Component({
  selector: 'app-pagos',
  imports: [DatePipe, ReactiveFormsModule],
  templateUrl: './pagos.html',
  styleUrl: './pagos.css',
})
export class Pagos {
  private readonly api = inject(PagosService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private solicitud: SolicitudPago | null = null;
  private filtros = { placa: '', desde: '', hasta: '' };

  protected readonly vista = signal<'consulta' | 'historial'>('consulta');
  protected readonly placa = new FormControl('', { nonNullable: true });
  protected readonly consultaForm = new FormGroup({ placa: this.placa });
  protected readonly historialForm = new FormGroup({
    placa: new FormControl('', { nonNullable: true }),
    desde: new FormControl('', { nonNullable: true }),
    hasta: new FormControl('', { nonNullable: true }),
  });
  protected readonly consulta = signal<ConsultaPago | null>(null);
  protected readonly recibo = signal<ComprobantePago | null>(null);
  protected readonly historial = signal<HistorialPago | null>(null);
  protected readonly ocupado = signal(false);
  protected readonly confirmar = signal(false);
  protected readonly error = signal('');
  protected readonly offset = signal(0);
  protected readonly limite = 20;
  protected readonly horaColombia = '-0500';

  protected readonly conceptos: Record<ConceptoPago, string> = {
    PRIMERA_MENSUALIDAD: 'Primera mensualidad',
    RENOVACION: 'Renovación',
    RENOVACION_CON_MORA: 'Renovación y regularización de mora',
  };

  protected tipoVehiculo(tipo: ConsultaPago['tipo']): string {
    return { MOTO: 'Moto', AUTOMOVIL: 'Automóvil', CAMIONETA: 'Camioneta' }[tipo];
  }

  protected moneda(importe: number): string {
    return '$' + new Intl.NumberFormat('es-CO', { minimumIntegerDigits: 1 }).format(importe) + ' COP';
  }

  protected estado(consulta: ConsultaPago): string {
    if (consulta.mora_pendiente.length) return 'Mora pendiente';
    if (consulta.vigencia_actual) return 'Vigente';
    if (!consulta.ultima_vigencia) return 'Sin mensualidad';
    return Date.parse(consulta.ultima_vigencia.inicio) > Date.now() ? 'Programada' : 'Vencida';
  }

  protected limpiarConsulta(): void {
    this.consulta.set(null);
    this.recibo.set(null);
    this.confirmar.set(false);
    this.error.set('');
    this.solicitud = null;
  }

  protected consultar(): void {
    const placa = this.placa.value.trim().toUpperCase();
    if (this.ocupado() || this.confirmar() || !placa) return;
    this.limpiarConsulta();
    this.placa.setValue(placa);
    this.ocupado.set(true);
    this.api.consultar(placa).pipe(
      finalize(() => this.ocupado.set(false)), takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (resultado) => this.consulta.set(resultado),
      error: (error: unknown) => this.mostrarError(error, 'No se pudo consultar la placa.'),
    });
  }

  protected prepararPago(): void {
    const consulta = this.consulta();
    if (!consulta || this.ocupado()) return;
    this.confirmar.set(true);
    this.error.set('');
  }

  protected registrar(): void {
    const consulta = this.consulta();
    if (!consulta || !this.confirmar() || this.ocupado()) return;
    this.solicitud ??= {
      placa: consulta.placa,
      importe: consulta.tarifa,
      solicitud_id: crypto.randomUUID(),
      ultima_vigencia_id: consulta.ultima_vigencia?.id ?? null,
      mora_pendiente_id: consulta.mora_pendiente[0]?.estancia_id ?? null,
    };
    this.error.set('');
    this.ocupado.set(true);
    this.api.registrar(this.solicitud).pipe(
      finalize(() => this.ocupado.set(false)), takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (recibo) => {
        this.limpiarConsulta();
        this.recibo.set(recibo);
      },
      error: (error: unknown) => {
        if (error instanceof HttpErrorResponse && [409, 422].includes(error.status)) {
          this.limpiarConsulta();
        }
        this.mostrarError(error, 'No se pudo confirmar el pago. Reintenta desde esta pantalla.');
      },
    });
  }

  protected cambiarVista(vista: 'consulta' | 'historial'): void {
    if (this.ocupado() || this.confirmar() || this.vista() === vista) return;
    this.vista.set(vista);
    this.recibo.set(null);
    this.error.set('');
    if (vista === 'historial') this.aplicarFiltros();
  }

  protected aplicarFiltros(): void {
    if (this.ocupado()) return;
    this.filtros = this.historialForm.getRawValue();
    this.filtros.placa = this.filtros.placa.trim().toUpperCase();
    this.cargarHistorial(0);
  }

  protected cargarHistorial(offset: number): void {
    if (this.ocupado()) return;
    this.error.set('');
    this.recibo.set(null);
    this.historial.set(null);
    this.ocupado.set(true);
    const { placa, desde, hasta } = this.filtros;
    this.api.historial(placa, desde, hasta, offset, this.limite).pipe(
      finalize(() => this.ocupado.set(false)), takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (resultado) => { this.historial.set(resultado); this.offset.set(offset); },
      error: (error: unknown) => this.mostrarError(error, 'No se pudo consultar el historial.'),
    });
  }

  protected abrirComprobante(id: number): void {
    if (this.ocupado()) return;
    this.error.set('');
    this.ocupado.set(true);
    this.api.comprobante(id).pipe(
      finalize(() => this.ocupado.set(false)), takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (recibo) => this.recibo.set(recibo),
      error: (error: unknown) => this.mostrarError(error, 'No se pudo abrir el comprobante.'),
    });
  }

  private mostrarError(error: unknown, alternativo: string): void {
    if (error instanceof HttpErrorResponse) {
      if (error.status === 401) void this.router.navigateByUrl('/iniciar-sesion');
      this.error.set(typeof error.error?.detail === 'string' ? error.error.detail : alternativo);
    } else {
      this.error.set(error instanceof TimeoutError ? alternativo : 'No se pudo completar la operación.');
    }
  }
}
