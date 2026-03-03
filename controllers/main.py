import json
from datetime import datetime, timedelta

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
        add_qty_raw = post.get("add_qty") or 1
        try:
            add_qty = int(float(add_qty_raw))
        except Exception:
            add_qty = 1
        if add_qty <= 0:
            add_qty = 1

        name = (post.get("name") or "").strip()
        date_start = post.get("date_start") or post.get("date_only")
        date_end = post.get("date_end") or date_start
        raw_date_range = post.get("date_range_list") or ""
        range_dates = []
        if raw_date_range:
            range_dates = [d for d in raw_date_range.split(",") if d]
            if range_dates and not date_start:
                date_start = range_dates[0]
            if range_dates and not date_end:
                date_end = range_dates[-1]
        schedule_id = post.get("schedule_id")
        valid_intention_types = {"1", "2", "3", "4"}

        intention_entries = []
        intention_field_pairs = [
            ("intention_type", "message"),
            ("intention_type_2", "message_2"),
            ("intention_type_3", "message_3"),
        ]
        for block_idx, (type_key, message_key) in enumerate(intention_field_pairs, start=1):
            block_type = (post.get(type_key) or "").strip()
            block_message = (post.get(message_key) or "").strip()

            if not block_type and not block_message:
                continue
            if block_type and block_type not in valid_intention_types:
                raise UserError(f"Tipo de intencion invalido en bloque {block_idx}.")
            if not block_type:
                raise UserError(f"Selecciona un tipo de intencion en bloque {block_idx}.")

            intention_entries.append({
                "intention_type": block_type,
                "message": block_message,
            })

        if not intention_entries:
            raise UserError("Debes capturar al menos una intención.")

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

        if not date_start:
            raise UserError("Debes indicar una fecha de inicio.")

        try:
            base_date_start = datetime.strptime(date_start, "%Y-%m-%d")
        except Exception:
            raise UserError("La fecha de inicio no es válida.")

        try:
            base_date_end = datetime.strptime(date_end, "%Y-%m-%d")
        except Exception:
            raise UserError("La fecha fin no es válida.")

        if base_date_end < base_date_start:
            raise UserError("La fecha fin debe ser mayor o igual a la fecha inicio.")

        days_in_range = (base_date_end - base_date_start).days + 1
        if days_in_range > add_qty:
            raise UserError("El rango de fechas excede la cantidad seleccionada.")
        selected_dates = [base_date_start + timedelta(days=offset) for offset in range(days_in_range)]
        if not range_dates:
            range_dates = [date_item.strftime("%Y-%m-%d") for date_item in selected_dates]

        schedule = None
        if schedule_id:
            try:
                schedule_id_int = int(schedule_id)
            except Exception:
                raise UserError("El horario seleccionado no es válido.")
            schedule = request.env["parish.chapel.mass_time"].sudo().browse(schedule_id_int)
            if not schedule.exists() or schedule.chapel_id.id != chapel.id:
                raise UserError("El horario seleccionado no pertenece a la capilla elegida.")

        # 5) Create intentions (1 a 3 bloques) por cada día seleccionado
        intention_vals_list = []
        for intention_entry in intention_entries:
            for day_date in selected_dates:
                intention_datetime = day_date
                if schedule and schedule.start_time:
                    try:
                        hour_str, minute_str = (schedule.start_time or "00:00").split(":")
                        intention_datetime = day_date.replace(
                            hour=int(hour_str),
                            minute=int(minute_str),
                            second=0,
                            microsecond=0,
                        )
                    except Exception:
                        intention_datetime = day_date

                intention_vals_list.append({
                    "name": intention_entry["message"] or name or product.display_name,
                    "partner_id": partner.id,
                    "message": intention_entry["message"],
                    "chapel_id": chapel.id,
                    "schedule_id": schedule.id if schedule else False,
                    "date_time": intention_datetime,
                    "date_start": day_date.date(),
                    "date_end": day_date.date(),
                    "date_range_text": ",".join(range_dates) if range_dates else None,
                    "amount": amount,
                    "website_id": request.website.id,
                    "state": "in_cart",
                    "intention_type": intention_entry["intention_type"],
                })

        intentions = request.env["parish.intention"].sudo().create(intention_vals_list)
        primary_intention = intentions[0]
        primary_intention_type = intention_entries[0]["intention_type"]

        # 6) Add product to cart
        res = order._cart_update(product_id=product.id, add_qty=add_qty)
        line = request.env["sale.order.line"].browse(res.get("line_id"))

        # 7) Customize sale order line
        line_name = product.display_name
        extra_bits = []

        if chapel:
            extra_bits.append(chapel.name)
        if date_start:
            date_range_text = date_start if date_end == date_start else f"{date_start} - {date_end}"
            extra_bits.append(date_range_text)
        if schedule and schedule.start_time:
            extra_bits.append(schedule.start_time)
        intention_type_labels = {
            "1": "Accion de gracias",
            "2": "Intencion especial",
            "3": "Difunto",
            "4": "Salud",
        }
        extra_bits.append(intention_type_labels.get(primary_intention_type, primary_intention_type))

        if extra_bits:
            line_name = f"{product.display_name} — " + " / ".join(extra_bits)

        line.sudo().write({
            "parish_intention_id": primary_intention.id,
            "name": line_name,
            "price_unit": amount if amount > 0 else line.price_unit,
        })

        intentions.sudo().write({"sol_id": line.id})

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
