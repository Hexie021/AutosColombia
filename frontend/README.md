# Interfaz de Autos Colombia

Angular standalone. Consultar el **README.md de la raíz** para preparar PostgreSQL y ejecutar la aplicación completa.

Desde esta carpeta:

```powershell
npm.cmd ci
npm.cmd start -- --host 127.0.0.1 --port 4200
```

Abrir http://127.0.0.1:4200/control-acceso. El proxy dirige `/operacion/**` al backend en el puerto 8000. Reiniciar Angular si cambia el proxy.

```powershell
npm.cmd run build
npm.cmd test -- --watch=false
```

La pantalla principal implementa entrada automática, comprobante imprimible, salida, pérdida del comprobante, corrección de celda, ocupación e historial. Los componentes de catálogo del profesor se conservan para futuras iteraciones y no forman parte de la navegación principal de esta EA1.
