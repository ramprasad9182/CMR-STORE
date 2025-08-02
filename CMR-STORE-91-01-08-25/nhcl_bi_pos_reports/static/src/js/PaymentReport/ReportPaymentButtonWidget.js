/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { PopupPaymentWidget } from "@nhcl_bi_pos_reports/js/PaymentReport/PaymentSummaryPopup";

export class ReportPaymentButtonWidget extends Component {
    static template = "nhcl_bi_pos_reports.ReportPaymentButtonWidget";

    setup() {
        this.pos = usePos();
    }

    async onClick(){
        var self = this;
        self.pos.popup.add(PopupPaymentWidget,{
            'title': 'Payment Summary',
        });
    }

    
}

ProductScreen.addControlButton({
    component: ReportPaymentButtonWidget,
    position: ["before", "SetFiscalPositionButton"],
    condition: function () {
        return this.pos.config.payment_summery;
    },
});
