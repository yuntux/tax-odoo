from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

import re
import unicodedata

from odoo.addons import base

class eventRegistration(models.Model):
    _inherit = "event.registration"
    

    @api.onchange('mail_auto')
    def _onchange_mail_auto(self):
        _logger.info('-- _onchange_mail_auto')
        if self.mail_auto:
            self.contact_user_link_id = False

    @api.onchange('contact_user_link_id')
    def _onchange_contact_user_link_id(self):
        if self.contact_user_link_id:
            self.mail_auto = False
        last_office365_mail_draft = False


    mail_auto = fields.Boolean(string="Mail auto", default=True)
    contact_user_link_id = fields.Many2one("taz.contact_user_link", "Responsable de l'invitation", domain="[('partner_id', '=', partner_id)]")
    registration_user_id = fields.Many2one("res.users", "User", related="contact_user_link_id.user_id", store=True)
    state = fields.Selection(selection_add=[
            ('identified', 'Identifié'),
            ('draft', 'Invité'), ('cancel', 'Annulé'),
            ('open', 'Confirmé'), ('done', 'Présent')
            ], default='identified')
    last_office365_mail_draft = fields.Text("Structure JSON de la réponse Office365")


    def get_html_invitation(self):
        self.ensure_one()
        
        form = ""
        if self.contact_user_link_id.formality :
            if self.contact_user_link_id.formality in ['tu_prenom','vous_prenom'] :
                form = self.partner_id.first_name
            elif self.contact_user_link_id.formality == 'vous_nom' :
                if self.partner_id.title.name :
                    form = self.partner_id.title.name + ' ' + self.partner_id.name
      
        return self.env['ir.ui.view']._render_template(self.event_id.invitation_mail_template.xml_id, {
                'event': self.event_id,
                'registration' : self,
                'formality' : form,
                'closing' : self.registration_user_id.first_name + ' ' + self.registration_user_id.name
            })



    def create_office365_mail_draft(self):
        for rec in self :
            if self.env.user.id != rec.registration_user_id.id:
                raise ValidationError(_("Seul la personne responsable de l'invitation peut générer le brouillon sur sa boîte email."))

            mail_dict = {
                    "subject":"Invitation - " +  str(rec.event_id.name),
                    #"importance":"Low",
                    "body":{
                        "contentType":"HTML",
                        "content": self.get_html_invitation(),
                    },
                    "toRecipients":[
                        {
                            "emailAddress":{
                                "address": rec.partner_id.email,
                            }
                        }
                    ],
                }
            if rec.event_id.invitation_cc_address :
                mail_dict['ccRecipients'] = [
                        {
                            "emailAddress":{
                                "address": rec.event_id.invitation_cc_address,
                            }
                        }
                    ]
            office365_mail_draft = self.env.user._msgraph_post_draft_mail(mail_dict)
            _logger.info(office365_mail_draft)
            rec.last_office365_mail_draft = office365_mail_draft