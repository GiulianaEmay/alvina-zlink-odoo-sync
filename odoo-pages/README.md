# odoo-pages — respaldo de páginas custom de Odoo

Páginas de Odoo (QWeb views) de Alviña, versionadas acá para no perderlas si
alguien las borra desde la interfaz de Odoo (como pasó con `/control-de-inventario`
antes de este respaldo).

## Páginas

| Archivo | URL en Odoo | Qué es |
|---|---|---|
| `rrhh-personal.view.xml` | `/rrhh/asistencia` | Módulo de Recursos Humanos: 7 cuadros (Asistencia, Tardanzas, Cumpleaños, Horarios y descansos, Ficha del personal, Pendientes de hoy, Reclutamiento bloqueado). Cálculo de tardanzas, agrupación por área, edición de ficha, asignación de turnos y descansos. Se conecta a `hr.employee`, `hr.attendance`, `resource.calendar`, `planning.slot`, `hr.leave`, `hr.department` y `ir.config_parameter` vía `/web/dataset/call_kw`. |

El `.meta.json` guarda los metadatos del view y la página web asociada
(id, nombre, key, modo, website, publicación). Sirve para reconstruir el
registro en `ir.ui.view` si se perdió, usando los IDs y campos originales.

## Cómo generar un respaldo nuevo

En la PC que corre el asistómetro (la misma que tiene `config.env` con las
credenciales de Odoo):

```
C:\AlvinaZlink\windows\backup_modulo_rrhh.bat
```

Eso genera los dos archivos en `C:\AlvinaZlink\odoo-pages\`. Luego hay que
copiarlos acá y hacer commit.

## Cómo restaurar

Si alguien borró el view desde Odoo, se puede recrear corriendo en una sesión
de Claude Code (o con un script `hr.employee`-equivalente):

```javascript
const arch = fs.readFileSync('odoo-pages/rrhh-personal.view.xml', 'utf-8');
await rpc('ir.ui.view','create',[{
  name: 'Personal', key: 'website.personal',
  type:'qweb', mode:'primary', website_id: 1, arch_db: arch
}]);
```

Luego recrear la `website.page` apuntando al nuevo view con la URL
`/rrhh/asistencia`.
