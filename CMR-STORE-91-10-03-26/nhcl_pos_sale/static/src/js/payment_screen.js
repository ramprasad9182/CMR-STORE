/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { Payment } from "@point_of_sale/app/store/models";

patch(PaymentScreen.prototype, {

    async validateOrder(isForceValidate) {
        const order = this.currentOrder;

        const cashAmount = order.paymentlines
            .filter(line => line.payment_method?.is_cash_count)
            .reduce((sum, line) => sum + line.amount, 0);

        if (cashAmount >= 200000) {
            await this.env.services.popup.add(ErrorPopup, {
                title: "Cash Limit Exceeded",
                body: "Cash payment is not allowed for amounts ₹200,000 and above.",
            });
            return false;
        }

        return super.validateOrder(isForceValidate);
    }


});

patch(Payment.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments); // Call the original setup method
        this.credit_note_id = 0;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.credit_note_id = this.credit_note_id || 0;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.credit_note_id = json.credit_note_id || 0;
    },

    set_credit_note(value) {
        this.credit_note_id = value;
    },
});