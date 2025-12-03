from odoo import models, fields


class ParishChapelMassTime(models.Model):
    _name = "parish.chapel.mass_time"
    _description = "Horario de misa por capilla"
    _order = "chapel_id, weekday, start_time"

    chapel_id = fields.Many2one(
        "parish.chapel",
        string="Capilla",
        required=True,
        ondelete="cascade",
    )

    name = fields.Char("Título", required=True)
    father_name = fields.Char("Sacerdote")

    # 0–6: día de la semana (alinear con tu dato; ver nota más abajo)
    weekday = fields.Selection(
        [
            ("0", "Domingo"),
            ("1", "Lunes"),
            ("2", "Martes"),
            ("3", "Miércoles"),
            ("4", "Jueves"),
            ("5", "Viernes"),
            ("6", "Sábado"),
        ],
        string="Día de la semana",
        required=True,
    )

    # Guardamos las horas como texto HH:MM, es suficiente y fácil de entender
    start_time = fields.Char("Hora inicio (HH:MM)", required=True)
    end_time = fields.Char("Hora fin (HH:MM)", required=True)

    schedule_type = fields.Selection(
        [
            ("available", "Disponible"),
            ("blocked", "Bloqueado"),
        ],
        string="Tipo de horario",
        default="available",
    )

    recur_type = fields.Selection(
        [
            ("none", "Único"),
            ("custom", "Recurrente (custom)"),
            ("workDays", "Días laborales"),
            ("allDays", "Todos los días"),
        ],
        string="Tipo de recurrencia",
        default="custom",
    )

    active = fields.Boolean("Activo", default=True)
