/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { Payment } from "@point_of_sale/app/store/models";

//if the employee gives discount beyond his limit then the manager needs to approve
patch(PaymentScreen.prototype, {
    /**
     * Override the validate button to approve discount limit
     */

    async validateOrder(isForceValidate) {
        const order = this.currentOrder;

        // Calculate TOTAL CASH used
        const cashAmount = order.paymentlines
            .filter(line => line.payment_method?.is_cash_count)
            .reduce((sum, line) => sum + line.amount, 0);

        console.log('===>cashAmount ',cashAmount)

        if (cashAmount >= 200000) {
            await this.env.services.popup.add(ErrorPopup, {
                title: "Cash Limit Exceeded",
                body: "Cash payment is not allowed for amounts ₹200,000 above.",
            });
            return false;
        }

        // continue normal validation
        return super.validateOrder(isForceValidate);
    },

    // manager pin validation

    async _finalizeValidation() {
        const order = this.pos.get_order();
        const cashier = this.pos.get_cashier();

        if (!order || !cashier) {
            return super._finalizeValidation(...arguments);
        }

        /* ---------- DISCOUNT ---------- */

        const lineDiscounts = order.get_orderlines().map(l => l.get_discount());
        const maxLineDiscount = Math.max(0, ...lineDiscounts);
        const globalDiscount = order.global_discount || 0;
        const effectiveDiscount = Math.max(maxLineDiscount, globalDiscount);

        const limit = cashier.limited_discount || 0;

        // No approval needed
        if (effectiveDiscount <= limit) {
            return super._finalizeValidation(...arguments);
        }

        /* ---------- MANAGER ---------- */

        if (!cashier.parent_id) {
            await this.popup.add(ErrorPopup, {
                title: _t("Manager Required"),
                body: _t("No manager assigned to this employee."),
            });
            return;
        }

        const managerId = cashier.parent_id[0];

        // ✅ CORRECT LOOKUP
        const manager = this.pos.employee_by_id?.[managerId];

        console.log("Cashier:", cashier);
        console.log("Manager:", manager);

        if (!manager || !manager.pin) {
            await this.popup.add(ErrorPopup, {
                title: _t("Manager PIN Missing"),
                body: _t("Manager PIN is not configured."),
            });
            return;
        }

        /* ---------- PIN POPUP ---------- */

        const { confirmed, payload } = await this.popup.add(NumberPopup, {
            title: _t("Manager Approval Required"),
            body: _t(
                `Discount exceeds allowed limit (${limit}%).\n` +
                `Enter manager PIN to continue.`
            ),
            isPassword: true,
        });

        if (!confirmed) {
            return;
        }

        // ✅ PLAIN TEXT COMPARISON (CORRECT FOR hr.employee.pin)
        if (payload !== manager.pin) {
            await this.popup.add(ErrorPopup, {
                title: _t("Invalid PIN"),
                body: _t("Incorrect manager PIN."),
            });
            return;
        }

        // Approved
        return super._finalizeValidation(...arguments);
    },


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