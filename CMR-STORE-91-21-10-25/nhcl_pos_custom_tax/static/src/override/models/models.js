/** @odoo-module */

import { Order, Orderline, Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { evaluateExpr, evaluateBooleanExpr } from "@web/core/py_js/py";

patch(Orderline.prototype, {
    get_applicable_taxes() {
        let lot_price =  this.get_unit_price();
        if (this.pack_lot_lines){
                 const packLotLines = this.pack_lot_lines;
                 let k;
                 packLotLines.forEach(pack => {
                    k = pack.lot_name
                 })
                   const stockLot = this.pos.stock_lots_by_name[k];
                   if (stockLot && stockLot.stockLot.rs_price >0){
                    lot_price = stockLot.stockLot.rs_price
                    }
     }
        var price_unit = lot_price * (1.0 - this.get_discount() / 100.0);
        price_unit = price_unit *(1.0-this.gdiscount/100.0);




        // Shenaningans because we need
        // to keep the taxes ordering.

         let taxes_ids;
                 if (this.product.taxes_id.length >= 2 ){
             var selectedTaxIds = [];
             for (let i = 0; i < this.product.taxes_id.length; i++) {
                        let taxBracket =  this.pos.taxes_by_id[this.product.taxes_id[i]]
                        if (price_unit >= taxBracket.min_amount && price_unit <= taxBracket.max_amount) {
                            selectedTaxIds = [this.product.taxes_id[i]]
                            break;
                        }
             }

              taxes_ids =  selectedTaxIds

        }
        else {

            taxes_ids = this.tax_ids || this.get_product().taxes_id
        }


          var i;
        var ptaxes_ids = this.tax_ids || taxes_ids
        var ptaxes_set = {};
        for (i = 0; i < ptaxes_ids.length; i++) {
            ptaxes_set[ptaxes_ids[i]] = true;
        }
        var taxes = [];
        for (i = 0; i < this.pos.taxes.length; i++) {
            if (ptaxes_set[this.pos.taxes[i].id]) {
                taxes.push(this.pos.taxes[i]);
            }
        }
        return taxes;
    },


get_taxes() {
     const product = this.get_product();
     let reward_original_product = false
     let lot_price =  this.get_unit_price();
     if (lot_price < 0) {
     lot_price = -(lot_price)
     }
      if (this.pack_lot_lines){
                const packLotLines = this.pack_lot_lines;
                     let k;
                     packLotLines.forEach(pack => {
                        k = pack.lot_name
                     })
                   const stockLot = this.pos.stock_lots_by_name[k];
                   if (stockLot && stockLot.stockLot.rs_price >0){
                    lot_price = stockLot.stockLot.rs_price
                    }
     }
     if (this.pack_lot_lines === false && this.is_reward_line == true){
          for (const line of this.order.orderlines) {
                // Check for dead tabs.
                if (line.product.id === this.reward_product_id)
                    {
                       if (line.pack_lot_lines){
                const packLotLines = line.pack_lot_lines;
                     let k;
                     packLotLines.forEach(pack => {
                        k = pack.lot_name
                     })
                   const stockLot = this.pos.stock_lots_by_name[k];
                   if (stockLot && stockLot.stockLot.rs_price >0){
                    lot_price = stockLot.stockLot.rs_price
                    reward_original_product = line.product
                    }
                }
            }
     }
     }
     let discount = parseFloat(this.get_discount()) || 0;
     let gdiscount = parseFloat(this.gdiscount) || 0;
     var price_unit = lot_price * (1.0 - discount / 100.0);
     price_unit = price_unit *(1.0- gdiscount/100.0);
    let taxes_ids;
    if (product.taxes_id.length >= 2) {
        let selectedTaxIds = [];
        for (let i = 0; i < product.taxes_id.length; i++) {
            let taxBracket = this.pos.taxes_by_id[product.taxes_id[i]];
            if (price_unit >= taxBracket.min_amount && price_unit <= taxBracket.max_amount) {
                selectedTaxIds = [product.taxes_id[i]];
                break;
            }
        }
        taxes_ids = selectedTaxIds;
    }
    else if (this.pack_lot_lines === false && this.is_reward_line == true && reward_original_product){
    if (reward_original_product.taxes_id.length >= 2) {
        let selectedTaxIds = [];
        for (let i = 0; i < reward_original_product.taxes_id.length; i++) {
            let taxBracket = this.pos.taxes_by_id[reward_original_product.taxes_id[i]];
            if (price_unit >= taxBracket.min_amount && price_unit <= taxBracket.max_amount) {
                selectedTaxIds = [reward_original_product.taxes_id[i]];
                break;
            }
        }
        taxes_ids = selectedTaxIds;
    }
    }
    if (this.reward_id && product.taxes_id.length >= 2) {
        let selectedTaxIds = [];
        for (let i = 0; i < product.taxes_id.length; i++) {
         const reward = this.pos.reward_by_id[this.reward_id];
        if (reward.reward_type == 'discount_on_product'){
            let taxBracket = this.pos.taxes_by_id[product.taxes_id[i]];
            let price_unit = reward.product_price
            if (price_unit >= taxBracket.min_amount && price_unit <= taxBracket.max_amount) {
                selectedTaxIds = [product.taxes_id[i]];
                break;
            }
        }
        }
        taxes_ids = selectedTaxIds;
    }


    else {
        taxes_ids = this.tax_ids || product.taxes_id;
    }
     if (taxes_ids) {
    taxes_ids = taxes_ids
    }
    else {
    taxes_ids = []
    }
    return this.pos.getTaxesByIds(taxes_ids);
},







       _getProductTaxesAfterFiscalPosition() {
        const product = this.get_product();

         let lot_price =  this.get_unit_price();

         let price_unit = lot_price * (1.0 - this.get_discount() / 100.0);

                price_unit = price_unit *(1.0-this.gdiscount/100.0);


        let taxesIds;
        if (product.taxes_id.length >= 2 ){
             let selectedTaxIds = [];
             for (let i = 0; i < product.taxes_id.length; i++) {
                        let taxBracket =  this.pos.taxes_by_id[product.taxes_id[i]]
                        if (price_unit >= taxBracket.min_amount && price_unit <= taxBracket.max_amount) {
                            selectedTaxIds = [product.taxes_id[i]]
                            break;
                        }
             }
              taxesIds =  selectedTaxIds
        }
        else {
            taxesIds = this.tax_ids || product.taxes_id;
        }

        taxesIds = taxesIds.filter((t) => t in this.pos.taxes_by_id);
        return this.pos.get_taxes_after_fp(taxesIds, this.order.fiscal_position);
    },


     get_all_prices(qty = this.get_quantity()) {
        let lot_price =  this.get_unit_price()
         let reward_original_product = false
        let discount = parseFloat(this.get_discount()) || 0;
        let gdiscount = parseFloat(this.gdiscount) || 0;
        var price_unit = lot_price * (1.0 - discount/ 100.0);
        price_unit = price_unit *(1.0- gdiscount/100.0);
        const order = this.pos.get_order();
        var taxtotal = 0;
        var product = this.get_product();
        if (this.is_reward_line == true){
          for (const line of this.order.orderlines) {
                // Check for dead tabs.
                if (line.product.id === this.reward_product_id)
                    {
                     reward_original_product = line.product
            }
     }
     }
        var taxes_ids;
        if (product.taxes_id.length >= 2 ){
             let selectedTaxIds = [];
             for (let i = 0; i < product.taxes_id.length; i++) {
                        let taxBracket =  this.pos.taxes_by_id[product.taxes_id[i]]
                        if (price_unit >= taxBracket.min_amount && price_unit <= taxBracket.max_amount) {
                            selectedTaxIds = [product.taxes_id[i]]
                            break;
                        }
             }
              taxes_ids =  selectedTaxIds
        }
         else if (this.is_reward_line == true && reward_original_product){
    if (reward_original_product.taxes_id.length >= 2) {
        let selectedTaxIds = [];
        for (let i = 0; i < reward_original_product.taxes_id.length; i++) {
            let taxBracket = this.pos.taxes_by_id[reward_original_product.taxes_id[i]];
            if (-(price_unit) >= taxBracket.min_amount && -(price_unit) <= taxBracket.max_amount) {
                selectedTaxIds = [reward_original_product.taxes_id[i]];
                break;
            }
        }
        taxes_ids = selectedTaxIds;
    }
    }
        else {
            taxes_ids = this.tax_ids  || product.taxes_id
        }
         if (taxes_ids) {
        taxes_ids = taxes_ids.filter((t) => t in this.pos.taxes_by_id);
        }
        else{
        taxes_ids = [];
        }
        var taxdetail = {};
        var product_taxes = this.pos.get_taxes_after_fp(taxes_ids, this.order.fiscal_position);
        console.log('product_taxes',product_taxes)
        var all_taxes = this.compute_all(
            product_taxes,
            price_unit,
            qty,
            this.pos.currency.rounding
        );
        var all_taxes_before_discount = this.compute_all(
            product_taxes,
            lot_price,
            qty,
            this.pos.currency.rounding
        );
        all_taxes.taxes.forEach(function (tax) {
            taxtotal += tax.amount;
            taxdetail[tax.id] = {
                amount: tax.amount,
                base: tax.base,
            };
        });
          return {
            priceWithTax: all_taxes.total_included,
            priceWithoutTax: all_taxes.total_excluded,
            priceWithTaxBeforeDiscount: all_taxes_before_discount.total_included,
            priceWithoutTaxBeforeDiscount: all_taxes_before_discount.total_excluded,
            tax: taxtotal,
            taxDetails: taxdetail,
        };
}




});

