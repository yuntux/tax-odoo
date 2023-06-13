from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

from datetime import datetime


class projectAccountingResPartner(models.Model):
     _inherit = "res.partner"

     def write(self, vals):
         for rec in self :
             if rec._precompute_protected() and not (self.env.user.has_group('account.group_account_user') or self.env.user.has_group('account.group_account_manager')):
                 raise ValidationError(_("Une fiche est protégée lorsqu'un objet comptable ou paracomptable (bon de commande client/fournisseur) le référence. Dans ce cas, la fiche ne peut être modifiée que par un ADV.\nVous ne pouvez pas modifier cette fiche entreprise car vous n'être pas ADV."))
         super().write(vals)

     def _precompute_protected(self):
        protected = False
        if self.is_company :
            if self.invoice_ids or self.sale_order_ids or self.purchase_order_count :
                protected = True
        return protected
        

     @api.depends('invoice_ids', 'sale_order_ids', 'purchase_order_count')
     def _compute_protected_partner(self):
         for rec in self:
             protected = rec._precompute_protected()
             rec.is_protected_partner = protected
        #TODO vérifier que invoices ids prend bien aussi les accoun.move liés par l'adresse de facturation/livraison


     @api.depends('project_ids', 'project_ids.date_start', 'project_ids.partner_id', 'project_ids.stage_is_part_of_booking')
     def compute_has_project_started_this_year(self):
         for rec in self:
             count = self.env['project.project'].search_count([
                            ('partner_id', '=', rec.id),
                            ('stage_is_part_of_booking', '=', True),
                            ('date_start', '>=', datetime.today().replace(month=1, day=1)),
                            ('date_start', '<=', datetime.today().replace(month=12, day=31))
                        ])
             res = False
             if count > 0 :
                 res = True
             rec.has_project_started_this_year = res

     def get_book_by_year(self, year):
         _logger.info('-- RES.PARTNER get_book_by_year')
         project_ids = self.env['project.project'].search([
                            ('partner_id', '=', self.id),
                            ('stage_is_part_of_booking', '=', True),
                        ])
         _logger.info(project_ids)
         res = 0.0
         for project in project_ids:
             res += project.get_book_by_year(year)
         _logger.info(res)
         return res

     project_ids = fields.One2many('project.project', 'partner_id', string="Projets")
     has_project_started_this_year = fields.Boolean('Un projet a débuté cette année', compute=compute_has_project_started_this_year, store=True)
     is_protected_partner = fields.Boolean('Fiche entreprise protégée', compute=_compute_protected_partner, help="Une fiche est protégée lorsqu'un objet comptable ou paracomptable (bon de commande client/fournisseur) le référence. Dans ce cas, la fiche ne peut être modifiée que par un ADV.")

     def _get_default_invoice_payement_bank_account_domain(self):
         return [('partner_id', '=', self.env.company.id)]

     default_invoice_payement_bank_account = fields.Many2one('res.partner.bank', 
             string="Compte bancaire de paiement", 
             help="Compte bancaire qui apparaitra par défaut sur les factures envoyées à ce client, et sur lequel le client devra payer la facture.", 
             domain=_get_default_invoice_payement_bank_account_domain)