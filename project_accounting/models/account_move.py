from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)
import json


class projectAccountingAccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info('---- create account.move')
        res_list = super().create(vals_list)
        for rec in res_list :
            rec._compute_linked_projects()
        return res_list

    def write(self, vals):
        _logger.info('---- write account.move')
        res = super().write(vals)
        for rec in self :
            rec._compute_linked_projects()
        return res

    def unlink(self):
        _logger.info('---- UNLINK account.move')
        old_rel_project_ids = self.rel_project_ids
        res = super().unlink()
        for project in old_rel_project_ids:
            project.compute()
        return res
    
    def _compute_linked_projects(self):
        for rec in self:
            for project in rec.rel_project_ids:
                project.compute()

    def comptute_project_ids(self):
        for rec in self:
            project_ids_res = []
            for line in self.line_ids:
                for p in line.rel_project_ids:
                    if p.id not in project_ids_res:
                        project_ids_res.append(p.id)
            if len(project_ids_res):
                rec.rel_project_ids = [(6, 0, project_ids_res)]
            else :
                rec.rel_project_ids = False

    rel_project_ids = fields.Many2many('project.project', string="Projets", compute=comptute_project_ids)

    @api.depends('bank_partner_id')
    def _compute_partner_bank_id(self):
        super()._compute_partner_bank_id()
        for move in self:
            if move.partner_id.default_invoice_payement_bank_account:
                move.partner_bank_id = move.partner_id.default_invoice_payement_bank_account
            #else :
            #    bank_ids = move.bank_partner_id.bank_ids.filtered(
            #        lambda bank: not bank.company_id or bank.company_id == move.company_id)
            #    move.partner_bank_id = bank_ids[0] if bank_ids else False
    # TODO : rendre le move.partner_bank_id obligatoire pour les factures clients (out_invoice)
        # si le partenr n'a pas de compte par defaut, l'ADV devra en mettre un manuellement sur la facture
    # TODO : quand move.partner_bank_id change ; sur le compte bancaire par défaut sur le partenaire n'est pas renseigner, proposer à l'utilisateur de l'ajouter sur la fiche du partner (wizzard de validation) 
    
    def _compute_payments_widget_to_reconcile_info(self):
        _logger.info('_compute_payments_widget_to_reconcile_info')

        super()._compute_payments_widget_to_reconcile_info()

        for move in self:
            payments_widget_vals = move.invoice_outstanding_credits_debits_widget
            if not payments_widget_vals:
                continue
            new_content = []

            #lines = move._compute_payments_widget_to_reconcile_info()
            _logger.info(payments_widget_vals['content'])
            for line in payments_widget_vals['content']:
                payments = self.env['account.payment'].search([('id', '=', line['account_payment_id'])])
                if len(payments):
                    payment = payments[0]
                    #On ne retient pas les paiements d'avance, s'ils ne concernent pas le sale.order d'au moins une des lignes de la factures
                    if payment.advance_sale_order_id and payment.advance_sale_order_id.id not in move.line_ids.sale_line_ids.order_id.ids :
                        continue
                    new_content.append(line)

            payments_widget_vals['content'] = new_content
            _logger.info(payments_widget_vals)
            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = len(new_content)

class projectAccountingAccountMoveLine(models.Model):
    _inherit = "account.move.line"
 
    @api.depends('price_subtotal', 'direction_sign')
    def _compute_price_subtotal_signed(self):
        for rec in self:
            rec.price_subtotal_signed = rec.price_subtotal * rec.direction_sign * -1

    @api.depends('price_total', 'direction_sign')
    def _compute_price_total_signed(self):
        for rec in self:
            rec.price_total_signed = rec.price_total * rec.direction_sign * -1

    @api.depends('move_id.amount_total', 'move_id.amount_residual', 'price_total')
    def _compute_amount_paid(self):
        for rec in self:
            if rec.parent_payment_state == 'reversed' :#or rec.parent_state != 'posted':
                #TODO : vérifier la conséquence si on supprimait la première clause : rec.parent_payment_state == 'reversed'
                _logger.info(rec.parent_payment_state)
                _logger.info(rec.parent_state)
                rec.amount_paid = 0.0
            else:
                invoice_amount_paid = rec.move_id.amount_total - rec.move_id.amount_residual
                rec.amount_paid = invoice_amount_paid * rec.direction_sign * -1 * (rec.price_total / rec.move_id.amount_total)

    parent_payment_state = fields.Selection(related='move_id.payment_state', store=True, string="État du paiement (fature)")
    parent_state = fields.Selection(string="État (fature)")
    amount_paid = fields.Monetary("Montant payé", compute=_compute_amount_paid)
    #TODO : stocker la valeur de ce champ : store=True

    direction_sign = fields.Integer(related="move_id.direction_sign", store=True)
    price_subtotal_signed = fields.Monetary(
        string='Montant HT (signé)',
        compute='_compute_price_subtotal_signed',
        store=True,
        currency_field='currency_id',
    )

    price_total_signed = fields.Monetary(
        string='Montant TTC (signé)',
        compute='_compute_price_total_signed',
        store=True,
        currency_field='currency_id',
    )
