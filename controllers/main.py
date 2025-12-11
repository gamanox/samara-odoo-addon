from datetime import datetime

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
        date_only = post.get("date_only")
        schedule_id = post.get("schedule_id")

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

        if not date_only:
            raise UserError("Debes indicar una fecha.")

        try:
            base_date = datetime.strptime(date_only, "%Y-%m-%d")
        except Exception:
            raise UserError("La fecha no es válida.")

        schedule = None
        if schedule_id:
            try:
                schedule_id_int = int(schedule_id)
            except Exception:
                raise UserError("El horario seleccionado no es válido.")
            schedule = request.env["parish.chapel.mass_time"].sudo().browse(schedule_id_int)
            if not schedule.exists() or schedule.chapel_id.id != chapel.id:
                raise UserError("El horario seleccionado no pertenece a la capilla elegida.")

        date_time = base_date
        if schedule and schedule.start_time:
            try:
                hour_str, minute_str = (schedule.start_time or "00:00").split(":")
                date_time = base_date.replace(hour=int(hour_str), minute=int(minute_str), second=0, microsecond=0)
            except Exception:
                date_time = base_date

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
        if date_only:
            extra_bits.append(date_only)
        if schedule and schedule.start_time:
            extra_bits.append(schedule.start_time)
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

    @http.route(['/shop/chapel/schedules'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def get_chapel_schedules(self, chapel_id=None, date_only=None, **post):
        chapel_id = chapel_id or post.get("chapel_id")
        date_only = date_only or post.get("date_only")

        if not chapel_id or not date_only:
            return {"schedules": []}

        try:
            chapel_id = int(chapel_id)
        except Exception:
            return {"schedules": []}

        chapel = request.env["parish.chapel"].sudo().browse(chapel_id)
        if not chapel.exists():
            return {"schedules": []}

        try:
            date_obj = datetime.strptime(date_only, "%Y-%m-%d").date()
        except Exception:
            return {"schedules": []}

        # Python weekday: Monday=0 ... Sunday=6. Data uses Sunday=0.
        python_weekday = date_obj.weekday()
        weekday = (python_weekday + 1) % 7
        weekday_str = str(weekday)

        schedules = request.env["parish.chapel.mass_time"].sudo().search([
            ("chapel_id", "=", chapel.id),
            ("schedule_type", "=", "available"),
            ("active", "=", True),
        ])

        def matches(schedule):
            # Siempre aplica para todos los días
            if schedule.recur_type == "allDays":
                return True
            # Días laborales: anclaje en weekday
            if schedule.recur_type == "workDays":
                if schedule.weekday == "1":
                    return weekday_str in {"1", "2", "3", "4", "5"}  # lunes a viernes
                if schedule.weekday == "2":
                    return weekday_str in {"2", "3", "4", "5", "6"}  # martes a sábado
                return weekday_str in {"1", "2", "3", "4", "5"}
            # Custom: coincide solo el día
            return schedule.weekday == weekday_str

        schedules = schedules.filtered(matches).sorted(key=lambda s: s.start_time or "")

        return {
            "schedules": [
                {
                    "id": sched.id,
                    "name": sched.name,
                    "start_time": sched.start_time,
                    "end_time": sched.end_time,
                    "father_name": sched.father_name,
                    "recur_type": sched.recur_type,
                }
                for sched in schedules
            ]
        }
