/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class OrderSummaryPopup extends Component {
    static template = "nhcl_pos_sale.OrderSummaryPopup";

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");

        this.summary = useState({
            gross: "0.00",
            discount: "0.00",
            netSale: "0.00",
            global_discount: "0.00",
            coupon_discount: "0.00", // 🆕
        });

        this.state = useState({
            showSummary: false,
        });
    }

    toggleSummary() {
        if (!this.state.showSummary) {
            this._recalculateSummary();
        }
        this.state.showSummary = !this.state.showSummary;
    }

    _recalculateSummary() {
        const order = this.pos.get_order();
        const orderlines = order.get_orderlines();

        let gross = 0;
        let discount = 0;
        let reward_discount = 0;
        let coupon_discount = 0;

        orderlines.forEach(line => {
            const price = Number(line.get_unit_price()) || 0;
            const qty = Number(line.quantity || line.qty) || 0;
            const line_total = price * qty;
            const line_discount_percent = Number(line.discount) || 0;

            if (line.is_reward_line) {
                // 🧠 Separate Gift Card from other reward discounts
                if (line.product?.display_name === "Gift Card") {
                    coupon_discount += Math.abs(line_total);  // Only to coupon
                } else {
                    reward_discount += Math.abs(line_total); // Other reward discounts
                }
                return;
            }

            gross += line_total;
            discount += line_total * (line_discount_percent / 100);
        });

        // Total real discount (excluding Gift Card)
        discount += reward_discount;

        const global_discount_percent = Number(orderlines[0]?.gdiscount) || 0;
        const subtotal = gross - discount- coupon_discount;
        const global_discount = subtotal * (global_discount_percent / 100);
const netSale = subtotal - global_discount;

        this.summary.gross = gross.toFixed(2);
        this.summary.discount = discount.toFixed(2);
        this.summary.global_discount = global_discount.toFixed(2);
        this.summary.netSale = netSale.toFixed(2);
        this.summary.coupon_discount = coupon_discount.toFixed(2); // ✅ Gift card discount only here
    }
}
