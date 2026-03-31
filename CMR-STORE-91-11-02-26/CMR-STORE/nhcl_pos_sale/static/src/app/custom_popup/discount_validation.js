///** @odoo-module */
//
//import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
//import { patch } from "@web/core/utils/patch";
//import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
//import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
//
//patch(PaymentScreen.prototype, {
//
//    async _finalizeValidation() {
//        console.log("==> _finalizeValidation TRIGGERED");
//
//        const order = this.pos.get_order();
//        const cashier = this.pos.get_cashier();
//
//        console.log("==> Cashier:", cashier);
//        console.log("==> Order:", order);
//
//        if (!order || !cashier) {
//            return super._finalizeValidation(...arguments);
//        }
//
//        const discounts = order.get_orderlines().map(l => l.get_discount());
//        const maxDiscount = Math.max(0, ...discounts);
//
//        console.log("==> Max Discount:", maxDiscount);
//
//        const autoLimit = 10;
//        const maxLimit = cashier.limited_discount || 0;
//
//        console.log("==> limited_discount:", maxLimit);
//
//        // 🔴 Hard block
//        if (maxDiscount > maxLimit) {
//            await this.popup.add(ErrorPopup, {
//                title: "Discount Not Allowed",
//                body: "Discount exceeds your maximum allowed limit.",
//            });
//            return;
//        }
//
//        // 🟡 Manager PIN
//        if (maxDiscount > autoLimit) {
//            const managerId = cashier.parent_id?.[0];
//            const manager = this.pos.employee_by_id?.[managerId];
//
//            console.log("==> Manager:", manager);
//
//            if (!manager || !manager.pin) {
//                await this.popup.add(ErrorPopup, {
//                    title: "Manager Missing",
//                    body: "Manager PIN is not configured.",
//                });
//                return;
//            }
//
//            const { confirmed, payload } = await this.popup.add(NumberPopup, {
//                title: "Manager Approval Required",
//                body: "Discount exceeds 10%. Enter manager PIN.",
//                isPassword: true,
//            });
//
//            console.log("==> Entered PIN:", payload);
//
//            if (!confirmed || payload !== manager.pin) {
//                await this.popup.add(ErrorPopup, {
//                    title: "Invalid PIN",
//                    body: "Incorrect manager PIN.",
//                });
//                return;
//            }
//        }
//
//        console.log("==> Validation passed");
//        return super._finalizeValidation(...arguments);
//    },
//});
