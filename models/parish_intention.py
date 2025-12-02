from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ParishIntention(models.Model):
    _name = "parish.intention"
    _description = "Mass Intention"
    _order = "date_time asc, id desc"

    name = fields.Char("Asunto", required=True)

    partner_id = fields.Many2one(
        "res.partner",
        string="Solicitante",
        required=True,
        default=lambda self: self.env.user.partner_id.id,
    )

    date_time = fields.Datetime("Fecha y hora", required=True)

    chapel_id = fields.Many2one(
        "parish.chapel",
        string="Lugar / Capilla",
        required=True,
    )

    message = fields.Text("Intención / Mensaje")

    amount = fields.Monetary("Ofrenda", currency_field="currency_id")

    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id.id,
    )

    website_id = fields.Many2one("website", string="Website")

    sol_id = fields.Many2one(
        "sale.order.line",
        string="Línea de venta",
        readonly=True,
        copy=False,
    )

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("in_cart", "En carrito"),
            ("paid", "Pagada"),
            ("done", "Realizada"),
            ("cancel", "Cancelada"),
        ],
        default="draft",
        tracking=True,
    )

    @api.constrains("date_time")
    def _check_future(self):
        for r in self:
            if r.date_time and r.date_time < fields.Datetime.now():
                raise ValidationError("La fecha/hora debe ser futura.")
