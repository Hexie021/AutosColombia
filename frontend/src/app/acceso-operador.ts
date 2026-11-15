import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize, Observable } from 'rxjs';
import { AccesoService } from './services/acceso.service';

@Component({
  selector: 'app-acceso-operador',
  imports: [FormsModule],
  template: `
    <section class="acceso">
      <h1>{{ cambio ? 'Cambiar contraseña' : 'Iniciar sesión' }}</h1>
      @if (aviso) { <p role="status">{{ aviso }}</p> }
      @if (error()) { <p role="alert">{{ error() }}</p> }
      <form (ngSubmit)="guardar()">
        @if (!cambio) {
          <label>Usuario <input name="usuario" autocomplete="username" [(ngModel)]="usuario" required maxlength="80"></label>
        }
        <label>{{ cambio ? 'Contraseña actual' : 'Contraseña' }}
          <input name="actual" type="password" autocomplete="current-password"
            [(ngModel)]="actual" required maxlength="128">
        </label>
        @if (cambio) {
          <label>Contraseña nueva <input name="nueva" type="password" autocomplete="new-password"
            [(ngModel)]="nueva" minlength="12" maxlength="128" required></label>
          <label>Confirmar contraseña <input name="confirmacion" type="password" autocomplete="new-password"
            [(ngModel)]="confirmacion" minlength="12" maxlength="128" required></label>
          <p>Usa al menos 12 caracteres.</p>
        }
        <button [disabled]="ocupado()">{{ cambio ? 'Guardar contraseña' : 'Iniciar sesión' }}</button>
      </form>
    </section>
  `,
  styles: `
    .acceso { max-width: 420px; padding: 2rem; margin: 2rem auto; background: white; border-radius: 12px; }
    form, label { display: grid; gap: .75rem; }
    label { margin-bottom: .4rem; }
    input, button { border: 1px solid #777; border-radius: 6px; padding: .65rem; font: inherit; }
    button { background: #ffc928; color: #191919; font-weight: bold; }
    [role=alert] { color: #a02626; }
  `,
})
export class AccesoOperador {
  private readonly acceso = inject(AccesoService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  readonly cambio = this.ruta.snapshot.data['cambio'] === true;
  readonly aviso = this.ruta.snapshot.queryParamMap.get('clave') === 'actualizada'
    ? 'Contraseña actualizada. Inicia sesión con la nueva.' : '';
  readonly ocupado = signal(false);
  readonly error = signal('');
  usuario = '';
  actual = '';
  nueva = '';
  confirmacion = '';

  guardar(): void {
    if (this.ocupado()) return;
    this.error.set('');
    if (!this.actual || (!this.cambio && !this.usuario.trim())) {
      this.error.set('Completa los campos de acceso.');
      return;
    }
    if (this.cambio && (this.nueva.length < 12 || this.nueva !== this.confirmacion)) {
      this.error.set('La contraseña nueva debe tener al menos 12 caracteres y coincidir con la confirmación.');
      return;
    }
    this.ocupado.set(true);
    const solicitud: Observable<unknown> = this.cambio ? this.acceso.cambiar(this.actual, this.nueva)
      : this.acceso.iniciar(this.usuario, this.actual);
    solicitud.pipe(finalize(() => this.ocupado.set(false))).subscribe({
      next: () => {
        if (this.cambio) {
          void this.router.navigate(['/iniciar-sesion'], { queryParams: { clave: 'actualizada' } });
        } else {
          void this.router.navigate(['/control-acceso']);
        }
      },
      error: (e: HttpErrorResponse) => {
        if (this.cambio && e.status === 401) {
          void this.router.navigate(['/iniciar-sesion']);
          return;
        }
        this.error.set(typeof e.error?.detail === 'string' ? e.error.detail : 'No se pudo completar la solicitud.');
      },
    });
  }
}
