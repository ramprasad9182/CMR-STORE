/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/store/models";

patch(Orderline.prototype, {

    getDisplayClasses() {
        const isProductScreen =
            this.pos.mainScreen.component?.name === "ProductScreen";

        return {
            ...super.getDisplayClasses(),
            "discount-highlight":
                isProductScreen && (this.is_reward_line || !!this.discount),
        };
    }

});
