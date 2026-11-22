import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import { API_BASE_URL } from './api.service';

interface Periodo {
  inicio: string;
  vencimiento: string;
}

interface Vigencia extends Periodo {
  id: number;
}

type Tipo = 'MOTO' | 'AUTOMOVIL' | 'CAMIONETA';
export type ConceptoPago = 'PRIMERA_MENSUALIDAD' | 'RENOVACION' | 'RENOVACION_CON_MORA';

export interface ConsultaPago {
  placa: string;
  tipo: Tipo;
  marca: string;
  cliente: string;
  tarifa: number;
  vigencia_actual: Vigencia | null;
  ultima_vigencia: Vigencia | null;
  mora_pendiente: { estancia_id: number; salida: string; operador: string }[];
  periodo_estimado: Periodo;
}

export interface SolicitudPago {
  placa: string;
  importe: number;
  solicitud_id: string;
  ultima_vigencia_id: number | null;
  mora_pendiente_id: number | null;
}

interface FilaPago {
  referencia: string;
  placa: string;
  fecha: string;
  concepto: ConceptoPago;
  importe: number;
  operador: string;
}

export interface ComprobantePago extends FilaPago {
  cliente: string;
  tipo: Tipo;
  vigencia: Vigencia;
  estancias_regularizadas: number[];
}

export interface HistorialPago {
  items: (FilaPago & { id: number })[];
  total: number;
}

@Injectable({ providedIn: 'root' })
export class PagosService {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL) + '/pagos';

  consultar(placa: string) {
    return this.http.get<ConsultaPago>(this.base + '/vehiculo/' + encodeURIComponent(placa))
      .pipe(timeout(15000));
  }

  registrar(solicitud: SolicitudPago) {
    return this.http.post<ComprobantePago>(this.base + '/mensualidad', solicitud).pipe(timeout(15000));
  }

  historial(placa: string, desde: string, hasta: string, offset: number, limit: number) {
    let params = new HttpParams().set('offset', offset).set('limit', limit);
    if (placa) params = params.set('placa', placa);
    if (desde) params = params.set('desde', desde);
    if (hasta) params = params.set('hasta', hasta);
    return this.http.get<HistorialPago>(this.base + '/historial', { params }).pipe(timeout(15000));
  }

  comprobante(id: number) {
    return this.http.get<ComprobantePago>(this.base + '/comprobante/' + id).pipe(timeout(15000));
  }
}
