/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";


patch(PaymentScreen.prototype, {
    async upiNewPaymentLine(paymentMethod) {
        const order = this.currentOrder;
        if (order.get_due() <= 0 && order.get_total_with_tax() > 0) {
            this.popup.add(ErrorPopup, {
                title: _t("No Due Amount"),
                body: _t("There is no due amount remaining for this order!"),
            });
            return false;
        }
        const same_paymentlines = order.paymentlines.filter(
            (paymentline) =>
                paymentline.payment_method.id === paymentMethod.id
        )
        if (same_paymentlines.length > 0) {
            this.popup.add(ErrorPopup, {
                title: _t("Payment Method Already Added"),
                body: _t("This payment method has already been added!"),
            });
            return false;
        }
        const restrictedPayments = [
            "Gift Voucher",
            "Credit Note Settlement",
            "Advance Payment",
        ];

        if (restrictedPayments.includes(paymentMethod.name)) {
            this.popup.add(ErrorPopup, {
                title: _t("Invalid Payment Method"),
                body: _t("The selected payment method cannot be added manually."),
            });
            return false;
        }

        return super.upiNewPaymentLine(...arguments);
    },
    addNewPaymentLine(paymentMethod) {
        const order = this.currentOrder;
        if (order.get_due() <= 0 && order.get_total_with_tax() > 0) {
            this.popup.add(ErrorPopup, {
                title: _t("No Due Amount"),
                body: _t("There is no due amount remaining for this order!"),
            });
            return false;
        }
        const same_paymentlines = order.paymentlines.filter(
            (paymentline) =>
                paymentline.payment_method.id === paymentMethod.id
        )
        if (same_paymentlines.length > 0) {
            this.popup.add(ErrorPopup, {
                title: _t("Payment Method Already Added"),
                body: _t("This payment method has already been added!"),
            });
            return false;
        }

        // Call original method if conditions pass
        return super.addNewPaymentLine(...arguments);
    },

    updateSelectedPaymentline(amount = false) {
        if (!this.selectedPaymentLine) {
            return;
        } // do nothing if no selected payment line

        const payment_method = this.selectedPaymentLine.payment_method;
        if (payment_method.is_credit_settlement) {
            this.popup.add(ErrorPopup, {
                title: _t("Payment Error"),
                body: _t("You can't change on Credit Note Settlement payment method!"),
            });
            return;
        } else if(payment_method.name === "Gift Voucher"){
            this.popup.add(ErrorPopup, {
                title: _t("Payment Error"),
                body: _t("You can't change on Gift Voucher payment method!"),
            });
            return;
        }
        const old_payment_line_amount = this.selectedPaymentLine.amount;

        const res = super.updateSelectedPaymentline(...arguments);

        if (payment_method.type === "bank") {
            if (amount === false) {
                if (this.numberBuffer.get() === null) {
                    amount = null;
                } else if (this.numberBuffer.get() === "") {
                    amount = 0;
                } else {
                    amount = this.numberBuffer.getFloat();
                }

            }
            const order = this.currentOrder;
            const change = order.get_change();
            if (amount && change) {
                this.selectedPaymentLine.set_amount(old_payment_line_amount);
                this.popup.add(ErrorPopup, {
                    title: _t("Bank Type Payment Error"),
                    body: _t("You can't set more than remaining payment on bank type payment method!"),
                });
                return;
            }
        }

        // Call original method if conditions pass
        return res;
    },
})
