import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AccesoService } from './services/acceso.service';

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly acceso = inject(AccesoService);
  private readonly router = inject(Router);
  readonly operador = this.acceso.operador;
  readonly errorSalida = signal('');

  cerrarSesion(): void {
    this.errorSalida.set('');
    this.acceso.cerrar().subscribe({
      next: () => void this.router.navigate(['/iniciar-sesion']),
      error: () => this.errorSalida.set('No se pudo cerrar la sesión. Intenta de nuevo.'),
    });
  }
}
