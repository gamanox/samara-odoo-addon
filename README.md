# parish_intentions_eshop

Addon para Odoo 17 que permite capturar intenciones de misa desde eCommerce (`/shop`) y enlazarlas con la línea de venta.

## Importante: nombre de carpeta

La carpeta del módulo **debe llamarse exactamente**:

`parish_intentions_eshop`

Si cambias el nombre, Odoo no lo reconocerá con ese nombre técnico y también fallará la referencia de assets declarada en `__manifest__.py`:

`parish_intentions_eshop/static/src/scss/style.scss`

## Requisitos

- Odoo 17
- Módulos instalados: `website_sale` y `sale_management` (dependencias declaradas en el manifest)

## Instalación en Odoo

1. Coloca la carpeta `parish_intentions_eshop` dentro de tu ruta de addons.
2. Reinicia el servicio de Odoo.
3. Actualiza la lista de apps (modo desarrollador recomendado).
4. Busca e instala el módulo **parish_intentions_eshop**.

También puedes actualizar por CLI:

```bash
odoo -d <tu_bd> -u parish_intentions_eshop
```

## Configuración después de instalar

1. En eCommerce, crea/ajusta el producto de intenciones con estos datos:
- Referencia interna (`default_code`) = `INTENTIONS`
- Publicado en el sitio web
- Variante disponible para venta
2. Configura capillas en `Ventas > Parroquia > Capillas`.
3. Configura horarios en `Ventas > Parroquia > Horarios por capilla` (`parish.chapel.mass_time`).
4. Opcional: el módulo carga datos demo/base en `data/chapel_data.xml` (capillas y horarios iniciales).

## Cómo funciona (según el código)

- El formulario especial solo aparece en la página de producto si `default_code == "INTENTIONS"`.
- El cliente debe seleccionar capilla, fecha inicio/fin, tipo de intención y horario.
- Los horarios se consultan por fecha y se muestran solo los que coinciden en todo el rango seleccionado.
- El rango de fechas no puede exceder la cantidad (`add_qty`) elegida del producto.
- Al enviar el formulario:
- Se crea un registro `parish.intention` con estado `in_cart`.
- Se agrega el producto al carrito y se vincula la línea de venta (`sale.order.line.parish_intention_id`).
- Si se envía monto (`amount`) mayor que 0, se usa como `price_unit` de la línea.
- Al confirmar el pedido de venta (`action_confirm`), la intención ligada pasa a estado `paid`.

## Modelos y menús que agrega

- `parish.intention` (intenciones)
- `parish.chapel` (capillas)
- `parish.chapel.mass_time` (horarios por capilla)
- `parish.chapel.schedule` (modelo adicional de horarios)

Menú principal:

`Ventas > Parroquia`
