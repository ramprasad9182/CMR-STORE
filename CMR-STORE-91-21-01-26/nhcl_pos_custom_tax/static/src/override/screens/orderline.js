///** @odoo-module */
//
//import { Order, Orderline, Payment } from "@point_of_sale/app/store/models";
//import { patch } from "@web/core/utils/patch";
//
//


//patch(Orderline.prototype, {
//    getDisplayData() {
//        var tax_details = {}
//        if ( this.get_tax_details() ){
//            var amount = 0.00;
//            var percentage = 0.00;
//            Object.values(this.get_tax_details()).forEach(tax => {
//                amount += parseFloat(tax.amount.toFixed(2));
//                percentage += tax.percentage
//                tax_details['base'] = tax.base;
//            });
//            tax_details['amount'] = amount;
//            tax_details['percentage'] = percentage;
////            tax_details['name'] = "GST "+ percentage.toString() +"%"
//        }
//
//        return {
//            ...super.getDisplayData(),
//            tax_details: tax_details
//        }
//    }
//})