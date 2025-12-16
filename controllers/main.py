import json
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
        user = request.env.user
        partner = user.partner_id
        is_public = getattr(user, "_is_public", lambda: False)()
        if not partner or is_public:
            partner = request.website.user_id.sudo().partner_id

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
        intention_type = post.get("intention_type")
        valid_intention_types = {"1", "2", "3", "4"}
        if intention_type and intention_type not in valid_intention_types:
            raise UserError("Tipo de intencion invalido.")

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
            "schedule_id": schedule.id if schedule else False,
            "date_time": date_time,
            "amount": amount,
            "website_id": request.website.id,
            "state": "in_cart",
            "intention_type": intention_type,
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
        if intention_type:
            intention_type_labels = {
                "1": "Accion de gracias",
                "2": "Intencion especial",
                "3": "Difunto",
                "4": "Salud",
            }
            extra_bits.append(intention_type_labels.get(intention_type, intention_type))
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

    @http.route(
        ['/shop/chapel/schedules'],
        type='http',
        auth="public",
        methods=['GET', 'POST'],
        website=True,
        csrf=False,
    )
    def get_chapel_schedules(self, chapel_id=None, date_only=None, **post):
        # Permite recibir JSON, formulario o querystring
        payload = {}
        try:
            payload = request.httprequest.get_json(silent=True) or {}
        except Exception:
            payload = {}

        def _json_response(payload):
            return request.make_response(
                json.dumps(payload),
                headers=[('Content-Type', 'application/json')],
            )

        chapel_id = chapel_id or payload.get("chapel_id") or post.get("chapel_id")
        # date_only manda el nombre de día (lunes-domingo) o la fecha; si no viene, caemos en date_value
        date_token = (
            date_only
            or payload.get("date_only")
            or post.get("date_only")
            or payload.get("date_value")
            or post.get("date_value")
        )

        if not chapel_id or not date_token:
            return _json_response({"schedules": []})

        try:
            chapel_id = int(chapel_id)
        except Exception:
            return _json_response({"schedules": []})

        chapel = request.env["parish.chapel"].sudo().browse(chapel_id)
        if not chapel.exists():
            return _json_response({"schedules": []})

        weekday_idx = None
        day_name_map = {
            "lunes": 0,
            "Lunes": 0,
            "martes": 1,
            "Martes": 1,
            "miercoles": 2,
            "miércoles": 2,
            "Miércoles": 2,
            "Miercoles": 2,
            "jueves": 3,
            "Jueves": 3,
            "viernes": 4,
            "Viernes": 4,
            "sabado": 5,
            "Sabado": 5,
            "Sábado": 5,
            "sábado": 5,
            "domingo": 6,
            "Domingo": 6,
        }

        if isinstance(date_token, (int, float)):
            weekday_idx = int(date_token)
        else:
            token_str = str(date_token).strip()
            # Intentar parsear fecha
            try:
                date_obj = datetime.strptime(token_str, "%Y-%m-%d").date()
                weekday_idx = date_obj.weekday()
            except Exception:
                # Intentar nombre de día
                weekday_idx = day_name_map.get(token_str.lower())
                if weekday_idx is None and token_str.isdigit():
                    weekday_idx = int(token_str)

        if weekday_idx is None or weekday_idx < 0 or weekday_idx > 6:
            return _json_response({"schedules": []})

        weekday_str = str(weekday_idx)

        schedules = request.env["parish.chapel.mass_time"].sudo().search([
            ("chapel_id", "=", chapel.id),
            ("weekday", "=", weekday_str),
        ])
        schedules = schedules.sorted(key=lambda s: s.start_time or "")

        result = {
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
            ],
           "week_day": weekday_str,
        }

        return _json_response(result)
