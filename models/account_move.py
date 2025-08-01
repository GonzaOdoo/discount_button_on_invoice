from odoo import models, fields,api
from collections import defaultdict

class AccountMoveDiscount(models.Model):
    _inherit = 'account.move'

    invoice_carrier_id = fields.Many2one(
        'delivery.carrier',
        string="Delivery Method",
        check_company=True,
        help="Transporte aplicado a esta factura."
    )

    def action_open_discount_wizard(self):
        self.ensure_one()
        return {
            'name': "Descuento",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.discount',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id,'default_company_id':self.company_id.id},
        }

    def action_open_delivery_wizard(self):
        self.ensure_one()
        return {
            'name': "Viaje",
            'type': 'ir.actions.act_window',
            'res_model': 'choose.delivery.carrier.invoice',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id,'default_company_id':self.company_id.id},
        }