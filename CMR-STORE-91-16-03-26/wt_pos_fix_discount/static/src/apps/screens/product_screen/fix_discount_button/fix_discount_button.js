/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { roundDecimals as round_di } from "@web/core/utils/numbers";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

export class SetFixDiscountButton extends Component {
    static template = "wt_pos_fix_discount.SetFixDiscountButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }
    async click() {
        // OLD
        // const selectedOrderline = this.pos.get_order().get_selected_orderline();
        // if (!selectedOrderline) {
        //     return;
        // }
        // const { confirmed, payload } = await this.popup.add(NumberPopup, {
        //     title: _t("Discount Fixed"),
        //     startingValue: 0,
        //     isInputSelected: true,
        // });
        // if (confirmed) {
        //     const price_unit = selectedOrderline.get_unit_price()
        //     const val = parseFloat(payload)
        //     selectedOrderline.set_fix_discount(val)
        // }

        const order = this.pos.get_order();
        const orderlines = order.get_orderlines();
//        const original_lines = orderlines.filter(line => !line.is_reward_line && !line.get_discount());
        const original_lines = orderlines.filter(line => !line.is_reward_line && (!line.get_discount() || (line.get_discount() && line.discount_reward)));
        if (original_lines.length < 1) {
            return;
        }
        let lines = original_lines.filter(line => line.select_order_line);
        if (!lines.length) {
            lines = original_lines;
        }

        let allow_fix_discount = true;
        lines.forEach(line => {
            if (line.get_gdiscount()) {
                allow_fix_discount = false;
            };
        });
        if (!allow_fix_discount) {
            this.pos.popup.add(ErrorPopup, {
                'title': _t("Global Discount Error"),
                'body': _t("A global discount is already applied to the cart!"),
            });
            return;
        }

        const { confirmed, payload } = await this.popup.add(NumberPopup, {
            title: _t("Amount Discount"),
            startingValue: 0,
            isInputSelected: true,
        });
        if (confirmed) {
            const val = parseFloat(
                round_di(parseFloat(payload) / lines.length, 2).toFixed(2)
            );
            lines.forEach(line => {
                line.set_fix_discount(val);
                line.select_order_line = false;
            });
            order._updateRewards();
        }

    }
}
ProductScreen.addControlButton({
    component: SetFixDiscountButton,
});