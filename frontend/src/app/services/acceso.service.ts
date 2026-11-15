import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of, tap } from 'rxjs';
import { API_BASE_URL } from './api.service';

interface OperadorEnSesion {
  id: number;
  nombre: string;
  usuario: string;
}

@Injectable({ providedIn: 'root' })
export class AccesoService {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL) + '/acceso';
  private readonly cuenta = signal<OperadorEnSesion | null>(null);
  readonly operador = this.cuenta.asReadonly();

  consultar() {
    return this.http.get<OperadorEnSesion>(this.base + '/sesion').pipe(
      tap((operador) => this.cuenta.set(operador)),
      catchError(() => {
        this.cuenta.set(null);
        return of(null);
      }),
    );
  }

  iniciar(usuario: string, contrasena: string) {
    return this.http.post<OperadorEnSesion>(this.base + '/iniciar', { usuario, contrasena })
      .pipe(tap((operador) => this.cuenta.set(operador)));
  }

  cerrar() {
    return this.http.post<void>(this.base + '/cerrar', {})
      .pipe(tap(() => this.cuenta.set(null)));
  }

  cambiar(actual: string, nueva: string) {
    return this.http.post<void>(this.base + '/contrasena', { actual, nueva })
      .pipe(tap(() => this.cuenta.set(null)));
  }
}

export const requiereOperador: CanActivateFn = () => {
  const router = inject(Router);
  return inject(AccesoService).consultar().pipe(
    map((operador) => operador ? true : router.createUrlTree(['/iniciar-sesion'])),
  );
};
