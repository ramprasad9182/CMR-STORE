/** @odoo-module */
import { Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { parseFloat as oParseFloat } from "@web/views/fields/parsers";
import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(Orderline.prototype, {
    setup() {
        super.setup(...arguments);
    },
    set_discount(discount) {
        var order = this.pos.get_order();
        if (order) {
            const orders = this.pos.get_order();
            const lines = orders.get_orderlines()
            const product = this.pos.db.get_product_by_id(this.pos.config.discount_product_id[0]);
//            const global_discount_product = lines.filter((line) => line.get_product() === product)
//            if (global_discount_product.length>0 && (discount !="" && discount !="remove")) {
//                            this.pos.popup.add(ErrorPopup, {
//                                'title': _t("Discount"),
//                                'body': _t("Global Discount has been Applied.For Item Discount ,Please Reset The Discount and Proceed!"),
//                            });
//                            return false
//                            }
//            else{
                var parsed_discount =
                typeof discount === "number"
                    ? discount
                    : isNaN(parseFloat(discount))
                    ? 0
                    : oParseFloat("" + discount);
                var disc = Math.min(Math.max(parsed_discount || 0, 0), 100);
                this.discount = disc;
                this.discountStr = "" + disc;
//            }
        }

    },
});