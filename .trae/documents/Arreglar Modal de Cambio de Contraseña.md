## Diagnóstico
- El modal mostrado corresponde a ChangePasswordModal.vue y aparece cuando must_change_password es true.
- La validación exige: mínimo 12 caracteres, al menos una mayúscula y un número.
- El mensaje “Las contraseñas no coinciden” indica que New/Confirm no son idénticas.
- Existen dos flujos duplicados: ChangePassword.vue (página) y ChangePasswordModal.vue (modal), lo que puede generar confusión.

## Qué hacer ahora (sin cambios de código)
- Usa la contraseña actual: admin.
- Introduce una nueva contraseña válida (ej. AdminSeguro1234) y repítela idéntica en Confirmar.
- Si el botón no se habilita, asegúrate de cumplir el mínimo de 12 caracteres, una mayúscula y un número.

## Mejoras propuestas (con cambios de código)
1. Unificar flujo
- Eliminar el modal y usar sólo ChangePassword.vue con ruta /change-password.
- Redirigir automáticamente tras éxito y borrar must_change_password.

2. UX y validación
- Deshabilitar el botón hasta que new/confirm coincidan y la regla se cumpla.
- Marcar claramente cuál requisito no se cumple y resaltar el campo que falla.
- Mantener los inputs en type="password" por defecto; sólo mostrar texto al pulsar el toggle.

3. Cierre automático del modal (si se mantiene)
- Tras éxito, cerrar el modal y redirigir a /dashboard.
- Sin duplicación de mensajes: usar i18n o strings consistentes.

4. Backend
- Confirmar que /api/users/change-password valida correctamente current_password y devuelve errores claros (incorrecto, política no cumple, etc.).

## Pruebas
- Añadir test backend del flujo de cambio de contraseña (válido/ inválido/ política).
- Probar e2e manual: login con admin, forzar cambio, actualizar, redirigir.

¿Confirmas que implemente la unificación al flujo de página y cierre automático? 