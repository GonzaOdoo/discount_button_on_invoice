from odoo import api, fields, models, SUPERUSER_ID, _, Command
from collections import defaultdict
from odoo.tools.float_utils import float_repr

class AccountMoveDiscount(models.TransientModel):
    _name = 'account.move.discount'
    _description = "Descuento en facturas"

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    move_id = fields.Many2one('account.move', required=True)
    discount_type = fields.Selection([
        ('line_discount', "Aplicar a todas las líneas"),
        ('global_discount','Descuento global'),
        ('fixed_amount', "Monto fijo"),
    ], default='line_discount')
    discount_percentage = fields.Float('Porcentaje')
    discount_amount = fields.Monetary('Monto a descontar')
    currency_id = fields.Many2one(related='move_id.currency_id')

    @api.constrains('discount_type', 'discount_percentage')
    def _check_discount_percentage(self):
        for record in self:
            if record.discount_type in ('line_discount', 'global_discount') and record.discount_percentage > 1.0:
                raise ValidationError(_("El porcentaje no puede ser mayor a 100%."))


    def _prepare_discount_product_values(self):
        """Return product.product used for discount line"""
        self.ensure_one()
        discount_product = self.company_id.sale_discount_product_id
        if not discount_product:
            # Verificar permisos para crear el producto
            if (
                self.env['product.product'].check_access_rights('create', raise_exception=False)
                and self.company_id.check_access_rights('write', raise_exception=False)
                and self.company_id.check_field_access_rights('write', ['sale_discount_product_id'])
            ):
                # Crear el producto con valores fijos, SIN llamar a este método
                product_vals = self._get_discount_product_creation_values()
                self.company_id.sale_discount_product_id = self.env['product.product'].create(product_vals)
                discount_product = self.company_id.sale_discount_product_id
            else:
                raise ValidationError(_(
                    "There does not seem to be any discount product configured for this company yet. "
                    "You can either use a per-line discount, or ask an administrator to set it up."
                ))
        return discount_product

    def _get_discount_product_creation_values(self):
        """Devuelve los valores para crear el producto de descuento, sin recursión."""
        return {
            'name': _("Descuento"),
            'detailed_type': 'service',  # o 'consu' si prefieres
            'taxes_id': False,
            'supplier_taxes_id': False,
            'company_id': self.company_id.id,
            'sale_ok': False,
            'purchase_ok': False,
            'list_price': 0.0,
            'standard_price': 0.0,
            'description_sale': _("Automatically generated discount product"),
        }
    def _prepare_discount_line(self, product, amount, taxes, description=None):
        """Prepare a discount line for the invoice."""
        self.ensure_one()
        return {
            'move_id': self.move_id.id,
            'product_id': product.id,
            'sequence': 9999,
            'name': description or _("Descuento"),
            'quantity': 1,
            'price_unit': -amount,
            'tax_ids': [Command.set(taxes.ids)],
        }

    def _apply_line_discounts(self):
        """Apply percentage discount to all invoice lines."""
        self.ensure_one()
        self.move_id.invoice_line_ids.write({
            'discount': self.discount_percentage * 100
        })

    def _create_global_discount_lines(self):
        """Create discount lines grouped by tax."""
        self.ensure_one()
        product = self._prepare_discount_product_values()

        total_per_tax = defaultdict(float)
        decimal_precision = self.env['decimal.precision'].precision_get('Discount')

        for line in self.move_id.invoice_line_ids:
            if not line.quantity or not line.price_unit:
                continue
            discounted_price = line.price_unit * (1 - (line.discount or 0.0) / 100)
            total_per_tax[line.tax_ids] += discounted_price * line.quantity

        if not total_per_tax:
            raise ValidationError(_("No hay lineas válidas para aplicar descuento"))

        vals_list = []
        for taxes, subtotal in total_per_tax.items():
            amount = subtotal * self.discount_percentage
            description = _(
                "Descuento: %(percent)s%%",
                percent=float_repr(self.discount_percentage * 100, decimal_precision),
            )
            if len(total_per_tax) > 1:
                description += _("\nOn lines with taxes: %(taxes)s", taxes=", ".join(taxes.mapped('name')))
            vals = self._prepare_discount_line(product, amount, taxes, description)
            vals_list.append(vals)

        self.env['account.move.line'].create(vals_list)

    def _create_fixed_amount_discount_line(self):
        """Create a single fixed-amount discount line."""
        product = self._prepare_discount_product_values()
        vals = self._prepare_discount_line(
            product=product,
            amount=self.discount_amount,
            taxes=self.env['account.tax'],
            description=_("Descuento monto fijo")
        )
        self.env['account.move.line'].create(vals)

    # --- MAIN ACTION ---

    def action_apply_discount(self):
        self.ensure_one()
        self = self.with_company(self.company_id)

        if self.discount_type == 'line_discount':
            self._apply_line_discounts()
        elif self.discount_type == 'global_discount':
            self._create_global_discount_lines()
        elif self.discount_type == 'fixed_amount':
            self._create_fixed_amount_discount_line()

        # Re-calcula la factura
        return {'type': 'ir.actions.act_window_close'}