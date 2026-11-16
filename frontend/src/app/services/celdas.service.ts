import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import { Celda, CeldaActualizar, CeldaCrear, CeldasPagina, FiltrosCeldas } from '../models/celda';

import { API_BASE_URL } from './api.service';

@Injectable({ providedIn: 'root' })
export class CeldasService {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);
  private readonly cells = `${this.base}/celdas`;

  list(offset: number, limit: number, filters: Partial<FiltrosCeldas> = {}) {
    const active = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
    return this.http
      .get<CeldasPagina>(this.cells, { params: { offset, limit, ...active } })
      .pipe(timeout(15000));
  }
  get(id: number) {
    return this.http.get<Celda>(`${this.cells}/${id}`).pipe(timeout(15000));
  }
  create(data: CeldaCrear) {
    return this.http.post<Celda>(this.cells, data).pipe(timeout(15000));
  }
  update(id: number, data: CeldaActualizar) {
    return this.http.patch<Celda>(`${this.cells}/${id}`, data).pipe(timeout(15000));
  }
  setEnabled(id: number, habilitada: boolean) {
    return this.http
      .patch<Celda>(`${this.cells}/${id}/habilitacion`, { habilitada })
      .pipe(timeout(15000));
  }
}

