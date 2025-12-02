from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    parish_intention_id = fields.Many2one("parish.intention", string="Intención", ondelete='set null')

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            for line in order.order_line:
                if line.parish_intention_id:
                    try:
                        line.parish_intention_id.sudo().write({'state': 'paid'})
                    except Exception:
                        pass
        return res
