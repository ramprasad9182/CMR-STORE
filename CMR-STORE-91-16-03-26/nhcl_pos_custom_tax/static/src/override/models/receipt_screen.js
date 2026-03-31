
/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useRef } from "@odoo/owl";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.buttonDupPrintReceipt = useRef("order-print-dup-receipt-button");
    },

    async printDupReceipt() {
        this.buttonDupPrintReceipt.el.className = "fa fa-fw fa-spin fa-circle-o-notch";
        let data = this.pos.get_order().export_for_printing();
        data.headerData.is_copy = true;
        const isPrinted = await this.printer.print(
            OrderReceipt,
            {
                data: {
                    ...data,
                    isBill: this.isBill,
                },
                formatCurrency: this.env.utils.formatCurrency,
            },
            { webPrintFallback: true }
        );

        if (isPrinted) {
            this.currentOrder._printed = true;
        }

        if (this.buttonDupPrintReceipt.el) {
            this.buttonDupPrintReceipt.el.className = "fa fa-print";
        }
    }

});
