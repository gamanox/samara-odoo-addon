from odoo import models, fields


class ParishChapel(models.Model):
    _name = "parish.chapel"
    _description = "Capilla / Lugar de misa"
    _order = "name"

    name = fields.Char("Nombre", required=True)
    code = fields.Char("Código interno")
    active = fields.Boolean("Activo", default=True)
