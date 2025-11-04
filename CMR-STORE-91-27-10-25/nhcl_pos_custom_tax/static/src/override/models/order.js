/** @odoo-module */

import { Order, Orderline, Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { roundDecimals, roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";

import { evaluateExpr, evaluateBooleanExpr } from "@web/core/py_js/py";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

function _newRandomRewardCode() {
    return (Math.random() + 1).toString(36).substring(3);
}


let pointsForProgramsCountedRules = {};

patch(Order.prototype, {

 setup(_defaultObj, options) {
       super.setup(...arguments);  // Call the original setup method

        // Initialize global discount
        this.global_discount = 0;
        this.is_rew = false;
        this.credit_note_amount = 0;
        this.credit_ids = [];
        this.credit_id = 0;
        this.credit_note_amounts = [];
        this.credit_partner;


                 if (!options.json) {
this.name = _t("%s %s", this.pos.company.company_short_code, this.uid);



    };

         // Initialize global discount
    },


    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
       json.credit_ids = this.credit_ids || [];
       json.credit_note_amounts = this.credit_note_amounts || [];
       json.credit_id = this.credit_id || 0;
        return json;
    },

    init_from_JSON(json) {

        super.init_from_JSON(...arguments);
        this.credit_ids = json.credit_ids || [];
        this.credit_note_amounts = json.credit_note_amounts || [];
        this.credit_id = json.credit_id || 0;
    },



     _isRewardProductPartOfRuleSerial(reward, product,currentline) {

        let max_discount = false;

        const totalProductQty = this.get_orderlines().filter((line) => line.product.id === product.id).reduce((sum, line) => sum + line.get_quantity(), 0);
        const totalProductValue = this.get_orderlines().filter((line) => line.product.id === product.id).reduce((sum, line) => sum + (line.get_quantity() * line.get_unit_price()), 0);

     if (currentline.pack_lot_lines){
        const packLotLines = currentline.pack_lot_lines;
                     let k;
                     packLotLines.forEach(pack => {
                        k = pack.lot_name
                     })
                   const stockLot = this.pos.stock_lots_by_name[k];
                   let lotId = stockLot.stockLot.id
              console.log(lotId)

        let enable_discount = false;
        if (
            reward.program_id.rules.filter(
                (rule) => rule.any_product || rule.valid_product_ids.has(product.id) && rule.serial_ids.has(lotId) && rule
            ).length > 0
        ) {

          for (const rule of reward.program_id.rules){

                 if (totalProductQty >= rule.minimum_qty && totalProductValue >= rule.minimum_amount){
                     enable_discount = true
                 }

                 let discount_amount = totalProductValue * (reward.discount/100)
                 console.log("1111111111",discount_amount)
                 if(reward.discount_max_amount > 0 && discount_amount>reward.discount_max_amount){

                   return true
                 }

          }

          if (enable_discount){

                currentline.set_discount(reward.discount)
                currentline.set_discount_reward(reward.id)
          }
          else {
                currentline.set_discount(0)
          }



        }


}

 if (max_discount == true){

    return true
 }

        return false
    },

    _getRewardLineValuesProduct(args) {
        const reward = args["reward"];
        const product = this.pos.db.get_product_by_id(
            args["product"] || reward.reward_product_ids[0]
        );

         let taxes_ids;
                 if (product.taxes_id.length >= 2 ){
             var selectedTaxIds = [];
             for (let i = 0; i < product.taxes_id.length; i++) {
                        let taxBracket =  this.pos.taxes_by_id[product.taxes_id[i]]
                        if (product.lst_price >= taxBracket.min_amount && product.lst_price <= taxBracket.max_amount) {
                            selectedTaxIds = [product.taxes_id[i]]
                            break;
                        }
             }

              taxes_ids =  selectedTaxIds

              console.log('price_unit',product)

              console.log(taxes_ids)

        }
        else {

            taxes_ids = product.taxes_id
        }




        const points = this._getRealCouponPoints(args["coupon_id"]);
        const unclaimedQty = this._computeUnclaimedFreeProductQty(
            reward,
            args["coupon_id"],
            product,
            points
        );
        if (unclaimedQty <= 0) {
            return _t("There are not enough products in the basket to claim this reward.");
        }
        const claimable_count = reward.clear_wallet
            ? 1
            : Math.min(
                  Math.ceil(unclaimedQty / reward.reward_product_qty),
                  Math.floor(points / reward.required_points)
              );
        const cost = reward.clear_wallet ? points : claimable_count * reward.required_points;
        // In case the reward is the product multiple times, give it as many times as possible
        const freeQuantity = Math.min(unclaimedQty, reward.reward_product_qty * claimable_count);
//        const orderLines = this.get_orderlines();
//        let price = 0.0
//        let enable_free_discount = false;
//        for (const currentline of orderLines) {
//            if (currentline.pack_lot_lines){
//                 const packLotLines = currentline.pack_lot_lines;
//                 let k;
//                 packLotLines.forEach(pack => {
//                        k = pack.lot_name
//                     })
//                 let lotId = 0
//                 const stockLot = this.pos.stock_lots_by_name[k];
//                 if (stockLot) {
//                 lotId = stockLot.stockLot.id
//                 }
//
//
//
//            for (const rule of reward.program_id.rules){
//                if (rule.any_product || rule.valid_product_ids.has(product.id) && rule.serial_ids.has(lotId))
//                   {
//                     price += currentline.price
//                     if (price >= rule.minimum_amount){
//                         enable_free_discount = true
//                      }
//                    console.log('price',price,rule.minimum_amount)
//
//                   }
//
//            }
//       }
//
//}
// if (enable_free_discount){
//                     return [
//            {
//                product: reward.discount_line_product_id,
//                price: -roundDecimals(
//                    product.get_price(this.pricelist, freeQuantity),
//                    this.pos.currency.decimal_places
//                ),
//                tax_ids: taxes_ids,
//                quantity: args["quantity"] || freeQuantity,
//                reward_id: reward.id,
//                is_reward_line: true,
//                reward_product_id: product.id,
//                coupon_id: args["coupon_id"],
//                points_cost: args["cost"] || cost,
//                reward_identifier_code: _newRandomRewardCode(),
//                merge: false,
//            },
//        ];
//
//
//                 }
console.log('free product',product.id)
console.log('discount_line_product_id',reward.discount_line_product_id)
                 return [
            {
                product: reward.discount_line_product_id,
                price: -roundDecimals(
                    product.get_price(this.pricelist, freeQuantity),
                    this.pos.currency.decimal_places
                ),
                tax_ids: taxes_ids,
                quantity: freeQuantity,
                reward_id: reward.id,
                is_reward_line: true,
                reward_product_id: product.id,
                coupon_id: args["coupon_id"],
                points_cost: args["cost"] || cost,
                reward_identifier_code: _newRandomRewardCode(),
                merge: false,
            },
        ];
    },

    _getDiscountableOnSpecific(reward) {

        const applicableProducts = reward.all_discount_product_ids;
        const linesToDiscount = [];
        const discountLinesPerReward = {};
        const orderLines = this.get_orderlines();
        const remainingAmountPerLine = {};
        for (const line of orderLines) {
            if (!line.get_quantity() || !line.price) {
                continue;
            }
            remainingAmountPerLine[line.cid] = line.get_price_with_tax();
            if (
                (applicableProducts.has(line.get_product().id)) && this._isRewardProductPartOfRuleSerial(reward,line.get_product(),line) ||
                (line.reward_product_id && applicableProducts.has(line.reward_product_id) && this._isRewardProductPartOfRuleSerial(reward,line.get_product(),line))
            ) {
                linesToDiscount.push(line);
            } else if (line.reward_id) {
                const lineReward = this.pos.reward_by_id[line.reward_id];
                if (lineReward.id === reward.id) {
                    linesToDiscount.push(line);
                }
                if (!discountLinesPerReward[line.reward_identifier_code]) {
                    discountLinesPerReward[line.reward_identifier_code] = [];
                }
                discountLinesPerReward[line.reward_identifier_code].push(line);
            }
        }

        let cheapestLine = false;
        for (const lines of Object.values(discountLinesPerReward)) {
            const lineReward = this.pos.reward_by_id[lines[0].reward_id];
            if (lineReward.reward_type !== "discount") {
                continue;
            }
            let discountedLines = orderLines;
            if (lineReward.discount_applicability === "cheapest") {
                cheapestLine = cheapestLine || this._getCheapestLine();
                discountedLines = [cheapestLine];
            } else if (lineReward.discount_applicability === "specific") {
                discountedLines = this._getSpecificDiscountableLines(lineReward);
            }
            if (!discountedLines.length) {
                continue;
            }
            const commonLines = linesToDiscount.filter((line) => discountedLines.includes(line));
            if (lineReward.discount_mode === "percent") {
                const discount = lineReward.discount / 100;
                for (const line of discountedLines) {
                    if (line.reward_id) {
                        continue;
                    }
                    if (lineReward.discount_applicability === "cheapest") {
                        remainingAmountPerLine[line.cid] *= 1 - discount / line.get_quantity();
                    } else {
                        remainingAmountPerLine[line.cid] *= 1 - discount;
                    }
                }
            } else {
                const nonCommonLines = discountedLines.filter(
                    (line) => !linesToDiscount.includes(line)
                );
                const discountedAmounts = lines.reduce((map, line) => {
                    map[line.get_taxes().map((t) => t.id)];
                    return map;
                }, {});
                const process = (line) => {
                    const key = line.get_taxes().map((t) => t.id);
                    if (!discountedAmounts[key] || line.reward_id) {
                        return;
                    }
                    const remaining = remainingAmountPerLine[line.cid];
                    const consumed = Math.min(remaining, discountedAmounts[key]);
                    discountedAmounts[key] -= consumed;
                    remainingAmountPerLine[line.cid] -= consumed;
                };
                nonCommonLines.forEach(process);
                commonLines.forEach(process);
            }
        }

        let discountable = 0;
        const discountablePerTax = {};
        let k = [];
        for (const line of linesToDiscount) {
             line.promo = reward.discount
                 k.push(line.product.id)
              console.log(k)
              line.get_all_prices()
            discountable += remainingAmountPerLine[line.cid];
            const taxKey = line.get_taxes().map((t) => t.id);
            if (!discountablePerTax[taxKey]) {
                discountablePerTax[taxKey] = 0;
            }
            discountablePerTax[taxKey] +=
                line.get_base_price() *
                (remainingAmountPerLine[line.cid] / line.get_price_with_tax());
        }
        return { discountable, discountablePerTax,k };
    },

        _getRewardLineValuesDiscount(args) {
        const reward = args["reward"];
        const coupon_id = args["coupon_id"];
        const rewardAppliesTo = reward.discount_applicability;
        let getDiscountable;
        if (rewardAppliesTo === "order") {
            getDiscountable = this._getDiscountableOnOrder.bind(this);
        } else if (rewardAppliesTo === "cheapest") {
            getDiscountable = this._getDiscountableOnCheapest.bind(this);
        } else if (rewardAppliesTo === "specific") {
            getDiscountable = this._getDiscountableOnSpecific.bind(this);
        }
        if (!getDiscountable) {
            return _t("Unknown discount type");
        }
        let { discountable, discountablePerTax ,k} = getDiscountable(reward);
        discountable = Math.min(this.get_total_with_tax(), discountable);
        if (!discountable) {
            return [];
        }
        let maxDiscount = reward.discount_max_amount || Infinity;
        if (reward.discount_mode === "per_point") {
            maxDiscount = Math.min(
                maxDiscount,
                reward.discount * this._getRealCouponPoints(coupon_id)
            );
        } else if (reward.discount_mode === "per_order") {
            maxDiscount = Math.min(maxDiscount, reward.discount);
        } else if (reward.discount_mode === "percent") {
            maxDiscount = Math.min(maxDiscount, discountable * (reward.discount / 100));
        }
        const rewardCode = _newRandomRewardCode();
        let pointCost = reward.clear_wallet
            ? this._getRealCouponPoints(coupon_id)
            : reward.required_points;
        if (reward.discount_mode === "per_point" && !reward.clear_wallet) {
            pointCost = Math.min(maxDiscount, discountable) / reward.discount;
        }
        // These are considered payments and do not require to be either taxed or split by tax
        const discountProduct = reward.discount_line_product_id;
        if (["ewallet", "gift_card"].includes(reward.program_id.program_type)) {
            return [
                {
                    product: discountProduct,
                    price: -Math.min(maxDiscount, discountable),
                    quantity: 1,
                    reward_id: reward.id,
                    is_reward_line: true,
                    coupon_id: coupon_id,
                    points_cost: pointCost,
                    reward_identifier_code: rewardCode,
                    merge: false,
                    tax_ids: [],
                },
            ];
        }
        const discountFactor = discountable ? Math.min(1, maxDiscount / discountable) : 1;
        const result = Object.entries(discountablePerTax).reduce((lst, entry) => {
            // Ignore 0 price lines
            if (!entry[1]) {
                return lst;
            }
            const taxIds = entry[0] === "" ? [] : entry[0].split(",").map((str) => parseInt(str));
            lst.push({
                product: discountProduct,
                price: -(entry[1] * discountFactor),
                quantity: 1,
                reward_id: reward.id,
                is_reward_line: true,
                coupon_id: coupon_id,
                points_cost: 0,
                reward_identifier_code: rewardCode,
                tax_ids: taxIds,
                merge: false,
                promodisclines: k

            });
            return lst;
        }, []);

        if (result.length) {
            result[0]["points_cost"] = pointCost;
        }
        return result;
    },

        set_orderline_options(line, options) {
        super.set_orderline_options(...arguments);
        if (options && options.is_reward_line) {
        let orderLines = line.order.get_orderlines()
            if (orderLines && orderLines[0].gdiscount) {
            line.gdiscount = orderLines[0].gdiscount
            }
            line.is_reward_line = options.is_reward_line;
            line.reward_id = options.reward_id;
            line.reward_product_id = options.reward_product_id;
            if (line.reward_product_id) {
            const product = this.pos.db.get_product_by_id(line.reward_product_id
        );
         if (product && product.tracking == 'serial')
        {
          line.quantity = 1;
        }
            }




            line.coupon_id = options.coupon_id;
            line.promodisclines = options.promodisclines;
            line.reward_identifier_code = options.reward_identifier_code;
            line.points_cost = options.points_cost;
            line.price_type = "automatic";
        }
        if (options && options.reward_id){
        line.reward_id = options.reward_id;
        }
        line.giftBarcode = options.giftBarcode;
        line.giftCardId = options.giftCardId;
        line.eWalletGiftCardProgram = options.eWalletGiftCardProgram;
    },






});
