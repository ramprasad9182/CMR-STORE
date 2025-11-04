/** @odoo-module */
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

export class CustomButton extends Component {
    static template = "pos_discount_manager.CustomButton";
    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }
    async click() {
        const order = this.pos.get_order();
        order.global_discount = 0
        const lines = order.get_orderlines();
        const line_discount_products = lines.filter((line) => line.discount > 0)
//        console.log(lines)
        const product = this.pos.db.get_product_by_id(this.pos.config.discount_product_id[0]);
//        console.log(product)
        const discount_product = lines.filter((line) => line.get_product() === product)
        if (discount_product.length === 0 && line_discount_products.length === 0) {
            await this.popup.add(ErrorPopup, {
                title: _t("No discount product found"),
                body: _t(
                    "Discount is Not Applied to Any Product."
                ),
            });
            return;
        }
        lines
            .filter((line) => line.get_product() === product)
            .forEach((line) => order._unlinkOrderline(line));
        if (line_discount_products.length > 0){
            for (let i = 0; i < line_discount_products.length; i++){
                const line_discount_value = 0
                line_discount_products[i].set_discount(line_discount_value);
            }

        }
     }
}
ProductScreen.addControlButton({
    component: CustomButton,
    condition: function () {
    return true;
    },
});