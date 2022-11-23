# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import _

import logging
_logger = logging.getLogger(__name__)

DOMAIN_EXCLUSION = "@tasmane.com"
    
class tazOfficePeople(models.TransientModel):
     _name = 'taz.office_people'
     _rec_name = 'display_name'
     first_name = fields.Char(string="Prénom")
     last_name = fields.Char(string="Nom")
     display_name = fields.Char(string="Office display name")
     parent_id = fields.Many2one('res.partner', string="Société", domain="[('is_company', '!=', False)]")
     odoo_id = fields.Char(string="Contact")
     already_in_odoo = fields.Boolean("Déjà sur Odoo")
     user_id = fields.Many2one('res.users', string="Propriétaire", required=True)
     origin_user_id = fields.Many2one('res.users', string="Utilisateur", required=True, readonly=True, help="Utilisateur Odoo du compte Office 365 qui a importé le contact - utilisé pour filtré") 
     email = fields.Char(string="email")
     category_id = fields.Many2many('res.partner.category', column1='taz_office_people_id',
                                    column2='category_id', string='Étiquettes clients')
     #user_id vendeur 

     def import_partner(self):
        model = self.env['res.partner']
        #Le passage par contexte permet de récupérer les valeurs du champ qui était en cours d'éditition lorsque l'utilisatuer a cliqué sur le bouton "Créer sur Odoo"
            # ça évite de perdre la
        self.category_id = self.env.context.get('category_id')
        self.parent_id = self.env.context.get('parent_id')
        self.first_name = self.env.context.get('first_name')
        self.last_name = self.env.context.get('last_name')
        self.user_id = self.env.context.get('user_id')

        #Créer le partner Odoo
        res = {
                    'first_name' : self.first_name,
                    'name' : self.last_name,
                    'email' : self.email,
                    'user_id' : self.env.user.id,
                    'parent_id' : self.parent_id.id, 
                    'is_company' : False,
                    'category_id' : self.category_id,
                    }
        r = model.create(res)
        _logger.info(r)
        self.odoo_id = r.id


     def open_res_partner(self):
        # first you need to get the id of your record
        # you didn't specify what you want to edit exactly
        rec_id = int(self.odoo_id)
        _logger.info(rec_id)
        # then if you have more than one form view then specify the form id
        form_id = self.env.ref("taz-common.contact_form")

        # then open the form
        return {
                'type': 'ir.actions.act_window',
                'name': 'Contact',
                'res_model': 'res.partner',
                'res_id': rec_id,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': form_id.id,
                'context': {},
                # if you want to open the form in edit mode direclty
                'flags': {'initial_mode': 'edit'},
                'target': 'new',
                #'target': 'current',
            }

     @api.model
     def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        #s'il n'y a aucun enregistrement pour l'utilisateur appeler get_office365_people
        _logger.info("=========== Search read pour l'utilisateur %s %s" % (self.env.user.id, self.env.user.name))
        if self.search([('user_id', '=', self.env.user.id)], count=True) == 0 :
            self.get_office365_people()
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs)
     
    #def refresh_office365_people(self): #TODO : ajouter un bouton de rafraichissement manuel
         #forcer le raffraichissement pour un utilisateur => pas sur que ça soit utile car le transienModel est vaccum toutes les heures
         #del all people for the current user
         #self.get_office365_people()

     def get_office365_people(self):
        _logger.info("=========== get_office365_people pour l'utilisateur %s %s" % (self.env.user.id, self.env.user.name))
        data = self.env.user._msgraph_people()
        _logger.info("=========== Nombre d'email retournés %s %s %s" % (str(len(data)), self.env.user.id, self.env.user.name))
        res = []

        mapping_email_id_contact = {}
        lc = self.env['res.partner'].search(['|', '|', ('email', '!=', False), ('personal_email', '!=', False), ('former_email_address', '!=', False), ('is_company', '=', False)])
        for c in lc:
            if c.email:
                mapping_email_id_contact[c.email.lower()] = c.id
            if c.personal_email:
                mapping_email_id_contact[c.personal_email.lower()] = c.id
            if c.former_email_address:
                for mail in c.former_email_address.split(','):
                    mapping_email_id_contact[mail.lower()] = c.id

        #TODO : ajouter une vue filtre avec par défaut le masquage des gens déjà dans Odoo
        #TODO : idée => ajouter un bouton d'exlucsion pour ne pas reproposer le contact ? => dans ce cas il ne faut pas un model Transient et il faut gérer la mise à jour en delta de ce qui vient d'Office
        for i in data :
            for mail in i["scoredEmailAddresses"]: #S'il y a plus d'une adresse pour un contact, c'est à  l'utilisateur de choisir quel contact créer sur Odoo
                if DOMAIN_EXCLUSION in mail["address"] :
                    continue
                # TODO couleur warning si nom / prénom existe déjà en base pour ne pas remettre des vieilles adresses email d'anciens postes
                computed_fname = ""
                computed_lname = ""
                l = mail["address"].split("@")[0].split('.')
                computed_fname = l[0].title()
                if (len(l) > 1):
                    computed_lname = '.'.join(l[1:]).upper()

                domain_target = mail["address"].split("@")[1]
                parent_id = None
                cl = self.env['res.partner'].search([('is_company', '=', 'True'),('child_mail_address_domain_list', 'like', domain_target)], order="write_date desc")
                if cl:
                    parent_id = cl[0].id

                odoo_id = None
                if mail["address"].lower() in mapping_email_id_contact.keys():
                    odoo_id = mapping_email_id_contact[mail["address"].lower()]

                already_in_odoo = False
                if odoo_id :
                    already_in_odoo = True

                res.append({
                    'display_name':i['displayName'],
                    'first_name' : computed_fname,
                    'last_name' : computed_lname,
                    'email' : mail["address"],
                    'user_id' : self.env.user.id,
                    'origin_user_id': self.env.user.id,
                    'parent_id' : parent_id, 
                    'odoo_id' : odoo_id,
                    'already_in_odoo' : already_in_odoo,
                    })
        self.create(res)

