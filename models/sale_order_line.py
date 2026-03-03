from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    parish_intention_id = fields.Many2one("parish.intention", string="Intención", ondelete='set null')

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()
        intention_model = self.env["parish.intention"].sudo()
        for order in self:
            for line in order.order_line:
                linked_intentions = intention_model.search([("sol_id", "=", line.id)])
                target_intentions = linked_intentions
                if line.parish_intention_id:
                    target_intentions |= line.parish_intention_id.sudo()
                if target_intentions:
                    target_intentions.write({"state": "paid"})
        return res
