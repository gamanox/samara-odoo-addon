from odoo import models, fields

class ParishChapelSchedule(models.Model):
    _name = "parish.chapel.schedule"
    _description = "Horarios de misa"

    chapel_id = fields.Many2one("parish.chapel", required=True)
    weekday = fields.Selection([
        ('0', 'Domingo'),
        ('1', 'Lunes'),
        ('2', 'Martes'),
        ('3', 'Miércoles'),
        ('4', 'Jueves'),
        ('5', 'Viernes'),
        ('6', 'Sábado'),
    ], required=True)
    start_time = fields.Char("Hora inicio", required=True)
    end_time = fields.Char("Hora fin", required=True)
    priest = fields.Char("Sacerdote")