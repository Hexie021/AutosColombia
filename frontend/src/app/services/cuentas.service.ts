import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import { API_BASE_URL } from './api.service';

export interface PerfilCuenta {
  nombre: string;
  telefono: string;
  usuario: string;
}

export interface CuentaOperador extends PerfilCuenta {
  id: number;
  activa: boolean;
}

export interface PaginaCuentas {
  items: CuentaOperador[];
  total: number;
}

@Injectable({ providedIn: 'root' })
export class CuentasService {
  private readonly http = inject(HttpClient);
  private readonly url = inject(API_BASE_URL) + '/acceso/cuentas';

  listar(offset: number, limit: number) {
    return this.http.get<PaginaCuentas>(this.url, { params: { offset, limit } }).pipe(timeout(15000));
  }

  crear(datos: PerfilCuenta & { contrasena: string }) {
    return this.http.post<CuentaOperador>(this.url, datos).pipe(timeout(15000));
  }

  editar(id: number, datos: PerfilCuenta & { activa: boolean; contrasena?: string }) {
    return this.http.put<CuentaOperador>(this.url + '/' + id, datos).pipe(timeout(15000));
  }
}
