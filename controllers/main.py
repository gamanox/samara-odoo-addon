from odoo import http
from odoo.http import request
from odoo.exceptions import UserError


class ParishIntentionsController(http.Controller):

    @http.route(['/shop/intention/add'], type='http', auth="public", methods=['POST'], website=True, csrf=True)
    def add_intention_to_cart(self, **post):
        # 1) Get or create current website sale order
        order = request.website.sale_get_order(force_create=True)

        # 2) Determine partner (logged in or public)
        partner = request.env.user.partner_id
        if not partner or partner._is_public():
            partner = request.env.ref("base.public_partner")

        # 3) Validate product
        product_id = post.get("product_id")
        if not product_id:
            raise UserError("Falta product_id en el formulario.")

        try:
            product_id = int(product_id)
        except Exception:
            raise UserError("product_id inválido.")

        product = request.env["product.product"].browse(product_id)
        if not product.exists():
            raise UserError("Producto no encontrado.")

        # 4) Read form data
        name = post.get("name") or ""
        message = post.get("message") or ""
        date_time = post.get("date_time")

        amount = 0.0
        if post.get("amount"):
            try:
                amount = float(post.get("amount"))
            except Exception:
                raise UserError("El monto de la ofrenda no es válido.")

        chapel_id = post.get("chapel_id")
        if not chapel_id:
            raise UserError("Selecciona un lugar / capilla.")

        try:
            chapel_id = int(chapel_id)
        except Exception:
            raise UserError("ID de capilla inválido.")

        chapel = request.env["parish.chapel"].sudo().browse(chapel_id)
        if not chapel.exists():
            raise UserError("La capilla seleccionada no existe.")

        if not date_time:
            raise UserError("Debes indicar fecha y hora.")

        # 5) Create the intention
        intention_vals = {
            "name": name or product.display_name,
            "partner_id": partner.id,
            "message": message,
            "chapel_id": chapel.id,
            "date_time": date_time,
            "amount": amount,
            "website_id": request.website.id,
            "state": "in_cart",
        }

        intention = request.env["parish.intention"].sudo().create(intention_vals)

        # 6) Add product to cart
        res = order._cart_update(product_id=product.id, add_qty=1)
        line = request.env["sale.order.line"].browse(res.get("line_id"))

        # 7) Customize sale order line
        line_name = product.display_name
        extra_bits = []

        if chapel:
            extra_bits.append(chapel.name)
        if date_time:
            extra_bits.append(date_time)
        if name:
            extra_bits.append(name)

        if extra_bits:
            line_name = f"{product.display_name} — " + " / ".join(extra_bits)

        line.sudo().write({
            "parish_intention_id": intention.id,
            "name": line_name,
            "price_unit": amount if amount > 0 else line.price_unit,
        })

        intention.sudo().write({"sol_id": line.id})

        # 8) Redirect to cart
        return request.redirect("/shop/cart")
