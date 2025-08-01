# models/choose_custom_delivery_carrier_invoice.py
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)
class ChooseCustomDeliveryCarrierInvoice(models.TransientModel):
    _name = 'choose.delivery.carrier.invoice'
    _description = 'Choose Custom Delivery Carrier for Invoice'

    move_id = fields.Many2one('account.move', required=True)
    carrier_id = fields.Many2one('delivery.carrier', required=True,string ="Método de envío")
    delivery_price = fields.Float( string ='Precio', readonly=True,)
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id')
    company_id = fields.Many2one('res.company', related='move_id.company_id', readonly=True)
    
    @api.onchange('carrier_id')
    def _onchange_carrier_id(self):
        if self.carrier_id and self.move_id:
            self.delivery_price = self._get_price_from_total(self.move_id.amount_untaxed)

    def _get_price_from_total(self, total):
        self.ensure_one()
        rules = self.carrier_id.price_rule_ids.sorted(lambda r: r.max_value)
    
        for rule in rules:
            _logger.info(rule)
            try:
                # Usamos 'max_value' en lugar de 'max_amount'
                test = eval(f"{total} {rule.operator} {rule.list_price}")
    
            except Exception as e:
                _logger.error("Error evaluando la regla %s: %s", rule.id, str(e))
                continue
    
            if test:
                # Calcula el precio usando base + porcentaje del monto
                _logger.info(rule.list_base_price + (total * rule.list_price / 100))
                return rule.list_base_price + (total * rule.list_price)
    
        return 0.0  # Si no aplica ninguna regla

    def button_confirm(self):
        self.ensure_one()
    
        # Volver a calcular el precio aquí, porque el valor de delivery_price podría haberse perdido
        if not self.carrier_id:
            return
    
        delivery_price = self._get_price_from_total(self.move_id.amount_untaxed)
    
        # Elimina líneas previas con el producto de envío
        product = self.carrier_id.product_id
        existing_lines = self.move_id.invoice_line_ids.filtered(
            lambda l: l.product_id == product
        )
        if existing_lines:
            existing_lines.unlink()
    
        # Crea línea de envío
        self.env['account.move.line'].create({
            'move_id': self.move_id.id,
            'product_id': product.id,
            'price_unit': -delivery_price if self.env.context.get('negative') else delivery_price,
            'quantity': 1,
            'name': "Acuerdos comerciales",
        })
    
        _logger.info("Precio de envío aplicado: %s", delivery_price)
