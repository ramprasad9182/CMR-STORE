/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { useService } from "@web/core/utils/hooks";
import { CustomButtonPopup } from "@nhcl_pos_sale/app/custom_popup/custom_popup";
import { Orderline,Order } from "@point_of_sale/app/store/models";
import { _t } from "@web/core/l10n/translation";
import { parseFloat as oParseFloat } from "@web/views/fields/parsers";


import {
    formatFloat,
    roundDecimals as round_di,
    roundPrecision as round_pr,
    floatIsZero,
} from "@web/core/utils/numbers";

patch(Orderline.prototype, {
    setup(_defaultObj, options) {
        // Call the original setup method
        super.setup(...arguments);
        // Initialize empNo
        this.empNo = this.empNo || "";
        this.badge ="";
        this.empId = this.empId || 0;
        this.proId = false;
        this.barcode = "";
        this.product_tax = "";
        this.product_mrp = "";
        this.discount_reward = 0;
         this.gdiscount = this.gdiscount || 0;
           this.promodisclines = [];
    },

    export_as_JSON() {
        // Call the original export_as_JSON method
        const json = super.export_as_JSON();
        // Return the extended JSON
        return {
            ...json,
            employe_no: this.get_emp_no(),
            badge_id: this.get_badge_id(),
            employ_id: this.get_employe_id(),
             gdiscount:this.get_gdiscount(),
             disc_lines:this.get_disclines(),
             discount_reward: this.get_discount_reward(),
        };
    },

    init_from_JSON(json) {
        // Call the original init_from_JSON method
        super.init_from_JSON(...arguments);
        // Set empNo from JSON
        this.set_emp_no(json.employe_no);
        this.set_badge_id(json.badge_id);
        this.set_employee_id(json.employ_id);
        this.set_gdiscount(json.gdiscount);
        this.set_discount_reward(json.discount_reward);
    },

    set_gdiscount(gdiscount){
    this.gdiscount = gdiscount

    },

    set_discount_reward(discount_reward){
    this.discount_reward = discount_reward

    },

   get_disclines() {

    return this.promodisclines
    },



    get_gdiscount(){

    return this.gdiscount;
    },

    get_discount_reward(){

    return this.discount_reward;
    },

    getDisplayData() {
    const lotName = this.pack_lot_lines.length > 0 ? this.pack_lot_lines[0].lot_name : null;

        console.log(this.pack_lot_lines)

        const stockLot = this.pos.stock_lots_by_name[lotName]


        const ref =  stockLot? stockLot.stockLot.ref:null
        const mrp =  stockLot? stockLot.stockLot.rs_price:null
         var tax = ""
        if (this.get_taxes().length>0){
            tax = this.get_taxes()[0].name
        }
        console.log("line",this)
        // Call the original getDisplayData method
        return {
            ...super.getDisplayData(),
            empNo: this.get_emp_no(),
            barcode:ref,
            product_tax: tax,
            product_mrp: mrp,
            gdiscount:this.get_gdiscount(),

        };
    },

//    can_be_merged_with(orderline) {
//        // Call the original can_be_merged_with method
//        const result = super.can_be_merged_with(orderline);
//        // Return the result of merge check including empNo comparison
//        return result && orderline.proId === true
//    },

    set_emp_no(no) {
        // Set empNo with default empty string if no value is provided
        this.empNo = no || "";
    },
    set_badge_id(no) {
        // Set empNo with default empty string if no value is provided
        this.badge = no || "";
    },

    set_employee_id(no) {
        // Set empNo with default empty string if no value is provided
        this.empId = no ;
    },


//   set_quantity(quantity, keep_price) {
//
//    // Check if the quantity is valid (0, 1, or -1)
//    if (quantity !== 0 && quantity !== 1 && quantity !== -1 && quantity!==''&& quantity !=='0' && quantity !=='1' && quantity !== '-1' && quantity!=='-') {
//        // If invalid, return early and prevent further processing
//        if (!this.comboParent) {
//           return
//        }
//        return false;
//    }
//    this.order.assert_editable();
//    var quant =
//        typeof quantity === "number" ? quantity : oParseFloat("" + (quantity ? quantity : 0));
//    // Handle refunded orderlines logic
//    if (this.refunded_orderline_id in this.pos.toRefundLines) {
//        const toRefundDetail = this.pos.toRefundLines[this.refunded_orderline_id];
//        const maxQtyToRefund =
//            toRefundDetail.orderline.qty - toRefundDetail.orderline.refundedQty;
//        if (quant > 0) {
//            if (!this.comboParent) {
//                this.env.services.popup.add(ErrorPopup, {
//                    title: _t("Positive quantity not allowed"),
//                    body: _t(
//                        "Only a negative quantity is allowed for this refund line. Click on +/- to modify the quantity to be refunded."
//                    ),
//                });
//            }
//            return false;
//        } else if (quant == 0) {
//            toRefundDetail.qty = 0;
//        } else if (-quant <= maxQtyToRefund) {
//            toRefundDetail.qty = -quant;
//        } else {
//            if (!this.comboParent) {
//                this.env.services.popup.add(ErrorPopup, {
//                    title: _t("Greater than allowed"),
//                    body: _t(
//                        "The requested quantity to be refunded is higher than the refundable quantity of %s.",
//                        this.env.utils.formatProductQty(maxQtyToRefund)
//                    ),
//                });
//            }
//            return false;
//        }
//    }
//
//    // Handle unit rounding
//    var unit = this.get_unit();
//    if (unit) {
//        if (unit.rounding) {
//            var decimals = this.pos.dp["Product Unit of Measure"];
//            var rounding = Math.max(unit.rounding, Math.pow(10, -decimals));
//            this.quantity = round_pr(quant, rounding);
//            this.quantityStr = formatFloat(this.quantity, {
//                digits: [69, decimals],
//            });
//        } else {
//            this.quantity = round_pr(quant, 1);
//            this.quantityStr = this.quantity.toFixed(0);
//        }
//    } else {
//        this.quantity = quant;
//        this.quantityStr = "" + this.quantity;
//    }
//
//    // Recompute the unit price if needed
//    if (!keep_price && this.price_type === "original") {
//        this.set_unit_price(
//            this.product.get_price(
//                this.order.pricelist,
//                this.get_quantity(),
//                this.get_price_extra()
//            )
//        );
//        this.order.fix_tax_included_price(this);
//    }
//
//    return true;
//},

    get_emp_no() {
        // Return empNo
        return this.empNo;
    },
    get_badge_id() {
        // Return empNo
        return this.badge;
    },

    get_employe_id() {
        // Return empNo
        return this.empId;
    },


    get_unit_price() {

       if (this.reward_product_id){
        let reward_product = this.order.get_orderlines().find(
            (line) => line.product.id === this.reward_product_id && line.product.tracking == 'serial');
            console.log('reward_product',reward_product)
            if (reward_product && reward_product.pack_lot_lines){
             const packLotLines = reward_product.pack_lot_lines;
                             let k;
                             packLotLines.forEach(pack => {
                                k = pack.lot_name
                             })
                           const stockLot = this.pos.stock_lots_by_name[k];
                           if (stockLot && stockLot.stockLot.rs_price >0){
                            lot_price = -(stockLot.stockLot.rs_price)
                            console.log('lot_price',lot_price)
                            return lot_price

                            }
             }
             return parseFloat(round_di(this.price || 0, digits).toFixed(digits));
     }

              else if (this.pack_lot_lines){
     const packLotLines = this.pack_lot_lines;
                     let k;
                     packLotLines.forEach(pack => {

                        k = pack.lot_name

                     })
                   const stockLot = this.pos.stock_lots_by_name[k];
                   if (stockLot && stockLot.stockLot.rs_price >0){
                   var lot_price = stockLot.stockLot.rs_price

                   console.log(lot_price)

                    return parseFloat(round_di(lot_price).toFixed(digits));
                    }
     } else {
     console.log('get unit price ',this)
        var digits = this.pos.dp["Product Price"];
        // round and truncate to mimic _symbol_set behavior
        return parseFloat(round_di(this.price || 0, digits).toFixed(digits));

     }
    },


       get_full_product_name() {
    const name = this.full_product_name || this.product.display_name || "";
    return name.split('(')[0].trim();
}

});
