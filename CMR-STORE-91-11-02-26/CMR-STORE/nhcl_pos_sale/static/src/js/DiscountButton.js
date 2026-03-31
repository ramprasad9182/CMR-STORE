/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { DiscountButton } from "@pos_discount/overrides/components/discount_button/discount_button";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";

patch(DiscountButton.prototype, {
    async click() {
        const order = this.pos.get_order();
        const lines = order.get_orderlines();
        const discount_products = lines.filter((line) => line.discount > 0);
        //        const selectedOrderline = this.pos.get_order().get_selected_orderline();
        var self = this;
        //        if (discount_products.length > 0){
        //            this.popup.add(ErrorPopup, {
        //                    title: _t("Discount"),
        //                    body: _t("Item Discount has been Applied.For Global Discount ,Please Reset The Discount and Proceed!"),
        //                });
        //                return false;
        //        }
        //        else
        //        {
        //          var self = this;
        const { confirmed, payload } = await this.popup.add(NumberPopup, {
            title: _t("Discount Percentage"),
            startingValue: this.pos.config.discount_pc,
        });
        if (confirmed) {
            const val = Math.round(
                Math.max(0, Math.min(100, parseFloat(payload)))
            );
            await self.apply_discount(val);
        }
        //        }
    },
    apply_discount(pc) {
        const order = this.pos.get_order();

        order.global_discount = pc;

        order._updateRewardLines();

        const lines = order.get_orderlines();
        for (const line of lines) {
            line.set_gdiscount(pc);
            const qty = line.get_quantity();
            const prices = line.get_all_prices(qty);
        }
    },
});
