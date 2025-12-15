/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { useService } from "@web/core/utils/hooks";
import { CustomButtonPopup } from "@nhcl_pos_sale/app/custom_popup/custom_popup";
import { Orderline, Order } from "@point_of_sale/app/store/models";
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
        this.badge = "";
        this.empId = this.empId || 0;
        this.proId = false;
        this.barcode = "";
        this.product_tax = "";
        this.product_mrp = "";
        this.discount_reward = 0;
        this.gdiscount = this.gdiscount || 0;
        this.promodisclines = [];
        this.discount_value = this.discount_value || 0;
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
            gdiscount: this.get_gdiscount(),
            disc_lines: this.get_disclines(),
            discount_reward: this.get_discount_reward(),
            discount_value: this.get_discount_value(),
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
        this.set_discount_value(json.discount_value);
    },

    set_gdiscount(gdiscount) {
        this.gdiscount = gdiscount;
    },

    set_discount_reward(discount_reward) {
        this.discount_reward = discount_reward;
    },

    set_discount_value(discount_value) {
        this.discount_value = parseFloat(
                round_di(discount_value || 0, 2).toFixed(2)
            );;
    },

    get_disclines() {
        return this.promodisclines;
    },

    get_gdiscount() {
        return this.gdiscount;
    },

    get_discount_reward() {
        return this.discount_reward;
    },

     get_discount_value() {
        return this.discount_value;
    },

    getDisplayData() {
        const lotName =
            this.pack_lot_lines.length > 0
                ? this.pack_lot_lines[0].lot_name
                : null;

        console.log(this.pack_lot_lines);

        const stockLot = this.pos.stock_lots_by_name[lotName];

        const ref = stockLot ? stockLot.stockLot.ref : null;
        let mrp = stockLot ? stockLot.stockLot.rs_price : null;
        //         if (this.reward_id){
        //        const reward = this.pos.reward_by_id[this.reward_id];
        //        if (reward.reward_type == 'discount_on_product'){
        //         mrp = reward.product_price
        //        }
        //        }
        var tax = "";
        if (this.get_taxes().length > 0) {
            tax = this.get_taxes()[0].name;
        }
        console.log("line", this);
        // Call the original getDisplayData method
        return {
            ...super.getDisplayData(),
            empNo: this.get_emp_no(),
            barcode: ref,
            product_tax: tax,
            product_mrp: mrp,
            gdiscount: this.get_gdiscount(),
            discount_value: this.get_discount_value(),
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
        this.empId = no;
    },

    async set_quantity(quantity, keep_price) {
        // Restrict serial-tracked products to qty = 1


        if (
            (this.product.nhcl_product_type === "unbranded" ||
                this.product.nhcl_product_type === "branded") &&
            this.product.tracking === "serial" &&
            quantity > 1
        ) {
            return this.pos.env.services.popup.add(ErrorPopup, {
                title: _t("Quantity Not Allowed"),
                body: _t(
                    "Serial-tracked products can only have quantity 1 per line."
                ),
            });

            quantity = 1; // Enforce quantity = 1
        }

        // Handle lot-tracked products
        else if (this.product.tracking === "lot" && this.pack_lot_lines) {

            try {
                const lot_name = this.pack_lot_lines.at(0).lot_name;

                // Fetch the lot record
                const lot_data = await this.pos.orm.call(
                    "stock.lot",
                    "search_read",
                    [
                        [["name", "=", lot_name]],
                        [
                            "id",
                            "name",
                            "product_id",
                            "location_id",
                            "product_qty",
                        ],
                    ]
                );

                if (lot_data.length > 0) {
                    const lot_id = lot_data[0].id;

                    const lot_qty_available = lot_data[0].product_qty;

                    // Prevent over-quantity
                    if (quantity > lot_qty_available) {
                        return this.pos.env.services.popup.add(ErrorPopup, {
                            title: _t("Not Enough Quantity"),
                            body: _t(
                                "Only " +
                                    lot_qty_available +
                                    " units are available in Lot " +
                                    lot_name
                            ),
                        });
                    }
                }
            } catch (error) {
                console.error("Error checking lot quantity:", error);
            }
            if (this.order) {
            this.order._updateRewards();
            }

        }
//this.order._updateRewards();
        // Apply quantity update if checks pass
         if (quantity === '0')
        {
        this.set_discount(0)
        }
        return super.set_quantity(quantity, keep_price);
    },

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
        const reward = this.pos.reward_by_id[this.reward_id];
        if (this.reward_product_id) {
            let reward_product = this.order
                .get_orderlines()
                .find((line) => line.product.id === this.reward_product_id);
            console.log("reward_product", reward_product);
            if (reward_product && reward_product.pack_lot_lines) {
                const packLotLines = reward_product.pack_lot_lines;
                let k;
                packLotLines.forEach((pack) => {
                    k = pack.lot_name;
                });
                const stockLot = this.pos.stock_lots_by_name[k];
                if (stockLot && stockLot.stockLot.rs_price > 0) {
                    lot_price = this.quantity * -stockLot.stockLot.rs_price;
                    console.log("lot_price", lot_price);
                    return lot_price;
                }
            }
            return parseFloat(
                round_di(this.price || 0, digits).toFixed(digits)
            );
        } else if (
            this.reward_id &&
            reward.reward_type == "discount_on_product"
        ) {
            if (reward.product_price > 0) {
                var lot_price = reward.product_price;
                return parseFloat(round_di(lot_price).toFixed(digits));
            }
        } else if (
        this.reward_id &&
        reward.buy_with_reward_price === "yes"
    ) {
        if (reward.reward_price > 0) {
            var lot_price = reward.reward_price/reward.buy_product_value;
            return lot_price;
        }
    }

        else if (this.pack_lot_lines) {
            const packLotLines = this.pack_lot_lines;
            let k;
            packLotLines.forEach((pack) => {
                k = pack.lot_name;
            });
            const stockLot = this.pos.stock_lots_by_name[k];
            if (stockLot && stockLot.stockLot.rs_price > 0) {
                var lot_price = stockLot.stockLot.rs_price;

                console.log(lot_price);

                return parseFloat(round_di(lot_price).toFixed(digits));
            }
        } else {
            console.log("get unit price ", this);
            var digits = this.pos.dp["Product Price"];
            // round and truncate to mimic _symbol_set behavior
            return parseFloat(
                round_di(this.price || 0, digits).toFixed(digits)
            );
        }
    },

    get_full_product_name() {
        const name = this.full_product_name || this.product.display_name || "";
        return name.split("(")[0].trim();
    },
});
