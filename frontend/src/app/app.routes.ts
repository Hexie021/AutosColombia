import { Routes } from '@angular/router';

import { requiereOperador } from './services/acceso.service';

export const routes: Routes = [
  {
    path: 'iniciar-sesion',
    loadComponent: () => import('./acceso-operador').then((m) => m.AccesoOperador),
  },
  {
    path: 'mi-cuenta',
    canActivate: [requiereOperador],
    data: { cambio: true },
    loadComponent: () => import('./acceso-operador').then((m) => m.AccesoOperador),
  },
  {
    path: 'control-acceso',
    canActivate: [requiereOperador],
    title: 'Control de acceso | Autos Colombia',
    loadComponent: () => import('./control-acceso/control-acceso').then((m) => m.ControlAcceso),
  },
  {
    path: 'gestion/operadores',
    canActivate: [requiereOperador],
    title: 'Operadores | Autos Colombia',
    loadComponent: () => import('./operadores/operadores').then((m) => m.Operadores),
  },
  {
    path: 'gestion/pagos',
    canActivate: [requiereOperador],
    title: 'Pagos | Autos Colombia',
    loadComponent: () => import('./pagos/pagos').then((m) => m.Pagos),
  },
  {
    path: 'gestion/celdas',
    canActivate: [requiereOperador],
    title: 'Celdas | Autos Colombia',
    loadComponent: () => import('./celdas/celdas').then((m) => m.Celdas),
  },
  { path: '', pathMatch: 'full', redirectTo: 'control-acceso' },
  {
    path: 'gestion/vehiculos',
    canActivate: [requiereOperador],
    title: 'Vehículos | Autos Colombia',
    loadComponent: () => import('./vehiculos/vehiculos').then((m) => m.Vehiculos),
  },
  { path: '**', redirectTo: '' },
];
