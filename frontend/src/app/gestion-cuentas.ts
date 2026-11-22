import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';

import { CuentaOperador, CuentasService, PaginaCuentas } from './services/cuentas.service';

@Component({
  selector: 'app-gestion-cuentas',
  imports: [FormsModule],
  template: `
    <section aria-labelledby="cuentas-titulo">
      <header>
        <h1 id="cuentas-titulo">Cuentas de operador</h1>
        <button type="button" class="principal" (click)="abrir()" [disabled]="ocupado()">Crear cuenta</button>
      </header>

      @if (aviso()) { <p role="status">{{ aviso() }}</p> }
      @if (error()) { <p role="alert">{{ error() }}</p> }

      @if (mostrandoFormulario()) {
        <form class="panel" (ngSubmit)="guardar()" #form="ngForm">
          <h2>{{ editando ? 'Editar cuenta' : 'Nueva cuenta de operador' }}</h2>
          <fieldset [disabled]="ocupado()">
            <label>Nombre <input name="nombre" [(ngModel)]="nombre" required maxlength="120"></label>
            <label>Teléfono <input name="telefono" [(ngModel)]="telefono" type="tel" required maxlength="120"></label>
            <label>Usuario <input name="usuario" [(ngModel)]="usuario" autocomplete="off" required maxlength="80"></label>
            <label>{{ editando ? 'Nueva contraseña (opcional)' : 'Contraseña inicial' }}
              <input name="contrasena" type="password" autocomplete="new-password" [(ngModel)]="contrasena"
                minlength="12" maxlength="128" [required]="!editando">
            </label>
            @if (!editando || contrasena) {
              <label>Confirmar contraseña
                <input name="confirmacion" type="password" autocomplete="new-password" [(ngModel)]="confirmacion"
                  minlength="12" maxlength="128" required>
              </label>
            }
            @if (editando) {
              <label class="estado"><input name="activa" type="checkbox" [(ngModel)]="activa"> Permitir inicio de sesión</label>
            }
          </fieldset>
          <div class="acciones">
            <button type="submit" class="principal" [disabled]="ocupado() || form.invalid">Guardar cuenta</button>
            <button type="button" [disabled]="ocupado()" (click)="cerrar()">Cancelar</button>
          </div>
        </form>
      }

      <div class="panel">
        <div class="tabla">
          <table>
            <thead><tr><th scope="col">Usuario</th><th scope="col">Nombre</th><th scope="col">Teléfono</th>
              <th scope="col">Estado</th><th scope="col">Acción</th></tr></thead>
            <tbody>
              @for (cuenta of pagina().items; track cuenta.id) {
                <tr>
                  <td>{{ cuenta.usuario }}</td><td>{{ cuenta.nombre }}</td><td>{{ cuenta.telefono }}</td>
                  <td>{{ cuenta.activa ? 'Activa' : 'Inactiva' }}</td>
                  <td><button type="button" [attr.aria-label]="'Editar ' + cuenta.usuario" [disabled]="ocupado()"
                    (click)="abrir(cuenta)">Editar</button></td>
                </tr>
              } @empty {
                <tr><td colspan="5">{{ ocupado() ? 'Cargando cuentas…' : 'No hay cuentas en esta página.' }}</td></tr>
              }
            </tbody>
          </table>
        </div>
        <div class="acciones">
          <span>{{ pagina().total }} cuentas</span>
          <button type="button" [disabled]="ocupado() || offset() === 0" (click)="cargar(offset() - limite)">Anterior</button>
          <button type="button" [disabled]="ocupado() || offset() + limite >= pagina().total"
            (click)="cargar(offset() + limite)">Siguiente</button>
        </div>
      </div>
    </section>
  `,
  styles: `
    section { padding-block: 24px 36px; }
    header, .acciones { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
    header { justify-content: space-between; }
    h1, h2 { margin: 0; }
    .panel { margin-top: 16px; background: #fff; border: 1px solid #d7d7da; border-radius: 8px; padding: 20px; }
    fieldset { border: 0; padding: 0; margin: 16px 0; display: grid; gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr)); }
    label { display: grid; gap: 6px; font-weight: 600; }
    label.estado { display: flex; align-items: center; align-self: end; min-height: 42px; }
    input, button { font: inherit; padding: 8px 12px; border: 1px solid #8a8a93; border-radius: 6px; background: #fff; }
    input:not([type=checkbox]) { min-width: 0; width: 100%; min-height: 42px; }
    button { font-weight: 600; min-height: 42px; cursor: pointer; }
    button:disabled { opacity: .55; cursor: default; }
    button.principal { background: #ffcf16; border-color: #ad8500; }
    :focus-visible { outline: 3px solid #986900; outline-offset: 2px; }
    .tabla { overflow-x: auto; margin-bottom: 12px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 9px; text-align: left; border-bottom: 1px solid #d7d7da; }
    [role=alert] { color: #a02626; }
  `,
})
export class GestionCuentas implements OnInit {
  private readonly api = inject(CuentasService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly pagina = signal<PaginaCuentas>({ items: [], total: 0 });
  readonly offset = signal(0);
  readonly limite = 20;
  readonly mostrandoFormulario = signal(false);
  readonly ocupado = signal(false);
  readonly error = signal('');
  readonly aviso = signal('');

  editando: number | null = null;
  nombre = '';
  telefono = '';
  usuario = '';
  contrasena = '';
  confirmacion = '';
  activa = true;

  ngOnInit(): void {
    this.cargar();
  }

  cargar(offset = 0): void {
    this.ocupado.set(true);
    this.error.set('');
    this.api.listar(offset, this.limite).pipe(
      takeUntilDestroyed(this.destroyRef), finalize(() => this.ocupado.set(false)),
    ).subscribe({
      next: (pagina) => { this.pagina.set(pagina); this.offset.set(offset); },
      error: (error: unknown) => this.mostrarError(error),
    });
  }

  abrir(cuenta?: CuentaOperador): void {
    this.editando = cuenta?.id ?? null;
    this.nombre = cuenta?.nombre ?? '';
    this.telefono = cuenta?.telefono ?? '';
    this.usuario = cuenta?.usuario ?? '';
    this.activa = cuenta?.activa ?? true;
    this.contrasena = this.confirmacion = '';
    this.error.set('');
    this.aviso.set('');
    this.mostrandoFormulario.set(true);
  }

  cerrar(): void {
    this.contrasena = this.confirmacion = '';
    this.mostrandoFormulario.set(false);
  }

  guardar(): void {
    if (this.ocupado()) return;

    this.error.set('');
    const perfil = { nombre: this.nombre.trim(), telefono: this.telefono.trim(), usuario: this.usuario.trim() };
    const id = this.editando;
    if (!perfil.nombre || !perfil.telefono || !perfil.usuario) {
      this.error.set('Completa el nombre, el teléfono y el usuario.');
      return;
    }
    if ((!id || this.contrasena) && (this.contrasena.length < 12 || this.contrasena !== this.confirmacion)) {
      this.error.set('Usa al menos 12 caracteres y verifica que ambas contraseñas coincidan.');
      return;
    }

    this.ocupado.set(true);
    const solicitud = id
      ? this.api.editar(id, { ...perfil, activa: this.activa, contrasena: this.contrasena || undefined })
      : this.api.crear({ ...perfil, contrasena: this.contrasena });
    solicitud.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.cerrar();
        this.aviso.set(id ? 'Cuenta actualizada.' : 'Cuenta de operador creada.');
        this.cargar(this.offset());
      },
      error: (error: unknown) => {
        this.ocupado.set(false);
        this.mostrarError(error);
      },
    });
  }

  private mostrarError(error: unknown): void {
    if (error instanceof HttpErrorResponse) {
      if (error.status === 401) void this.router.navigateByUrl('/iniciar-sesion');
      if (error.status === 403) void this.router.navigateByUrl('/control-acceso');
      if (typeof error.error?.detail === 'string') {
        this.error.set(error.error.detail);
        return;
      }
    }
    this.error.set('No fue posible completar la solicitud. Intenta de nuevo.');
  }
}
