# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _
import requests

import logging
_logger = logging.getLogger(__name__)


class tazResUsers(models.Model):
    _inherit = "res.users"

    def name_get(self):
         res = []
         for rec in self:
            res.append((rec.id, "%s %s" % (rec.first_name or "", rec.name or "")))
         return res

    
    def _get_valid_access_token(self):
        #TODO : tester la date de fin de validité du token
            # si dépassée, tenter de le raffraichir avec le refresh token
        return self.oauth_access_token

    def _magraph_post(self, endpoint, data):
        _logger.info('Envoi requete POST à %s avec le corps %s' % (endpoint, data))
        access_token = self._get_valid_access_token()
        req = requests.post(endpoint, json=data, headers={'Authorization': 'Bearer %s' % access_token}, timeout=10) 
        _logger.info(req.text)
        if req.ok:
            return req.json()
        else :
            _logger.info(req.text)


    def _magraph_patch(self, endpoint, data, ifmatch):
        _logger.info('Envoi requete PATCH à %s le corps %s avec le header ifMatch %s' % (endpoint, data, ifmatch))
        access_token = self._get_valid_access_token()
        req = requests.patch(endpoint, json=data, headers={'Authorization': 'Bearer %s' % access_token, 'If-Match' : ifmatch, 'Prefer' : 'return=representation'}, timeout=10) 
        _logger.info(req.text)
        if req.ok:
            return req.json()
        else :
            #TODO : si code erreur de mauvaise version, trigger la dernière version et rejouter patch ?
            #TODO : si la task a été supprimée sur Planner ?
            _logger.info(req.text)

    @api.model
    def _msgraph_people(self):
        tk = self._get_valid_access_token()
        if not self.oauth_provider_id or not tk or 'microsoft' not in self.oauth_provider_id.data_endpoint:
            #TODO : pourquoi lorsque je lève l'exception suivante, le front plante au lieu d'afficher le message ?
            #raise ValidationError(_('Vous ne vous êtes pas connecté à Odoo avec le SSO Office 365 ou votre compte utilisateur est mal configuré. Nous ne pouvons pas lire les contacts auprès de l\'API Microsoft.'))
            return []
        #TODO : forcer le rafraichissment du token

        contacts = []
        offset = 0
        while (True) :
            # DOCUMENTATION : https://docs.microsoft.com/fr-fr/graph/people-example
            endpoint = self.oauth_provider_id.data_endpoint + '/people?$top='+str(MSGRAPH_PAGE_SIZE)+'&select=displayName,scoredEmailAddresses&skip='+str(offset)
            graphdata = self._auth_oauth_rpc(endpoint, tk)
            if "value" not in graphdata.keys():
                #TODO : pourquoi lorsque je lève l'exception suivante, le front plante au lieu d'afficher le message ?
                #raise AccessError(_('Jeton Office 365 périmé. Merci de vous déconnecter d\'Odoo et de vous y reconnecter via Office 365'))
                return []
            contacts.extend(graphdata["value"])
            if (len(graphdata["value"]) < MSGRAPH_PAGE_SIZE):
                break
            offset = offset + MSGRAPH_PAGE_SIZE
        return contacts
