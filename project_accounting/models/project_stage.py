from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class projectStage(models.Model):
    _inherit = "project.project.stage"

    is_part_of_booking = fields.Boolean('Compte dans le book', help="Les projects qui sont à cette étape comptent dans le book.")
    state = fields.Selection([
        ('before_launch', 'Projet pas encore lancé (avant le lancement)'),
        ('launched', 'Projet lancé (mission en cours)'),
        ('closed', 'Projet terminé ou annulé ou perdu'),
        ], string="Etat")
    color = fields.Selection([
            ('decoration-danger', 'Rouge'),
            ('decoration-info', 'Bleu'),
            ('decoration-muted', 'Gris'),
            ('decoration-primary', 'Rose'),
            ('decoration-success', 'Vert'),
            ('decoration-warning', 'Marron'),
        ], "Couleur")

