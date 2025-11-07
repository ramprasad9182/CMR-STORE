/** @odoo-module */
import { CustomButtonPopup } from "@nhcl_pos_sale/app/custom_popup/custom_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { CustomSearch } from "@nhcl_pos_sale/app/screens/product_screen/custom_search/custom_search";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { Packlotline } from "@point_of_sale/app/store/models";

patch(ProductScreen.prototype, {

    setup() {
        super.setup();
        this.pos = usePos();
        this.orm = useService("orm");
        this.popup = useService("popup");
    },



    async _barcodeProductAction(code) {
    let self = this;
    let selectedOrder = this.pos.get_order();
    let barcode = this.env.services.pos.barcode_by_name[code.base_code];
    if (barcode) {
        let products = [];
        if (barcode.product_id) {
            let product = this.env.services.pos.db.get_product_by_id(barcode.product_id[0]);
            console.log("sss", product);
            const orderlines = await this.currentOrder.orderlines;
            let lotNames = []; // Ensure lotNames is declared

            orderlines.forEach(orderline => {
                if (orderline.product.tracking == 'serial' && orderline.pack_lot_lines.length > 0) {
                    const packLotLines = orderline.pack_lot_lines;
                    packLotLines.forEach(packLotLine => {
                        if (packLotLine.lot_name) {
                            lotNames.push(packLotLine.lot_name);
                        } else {
                            console.log('packLotLine.lot_name is missing or invalid');
                        }
                    });
                }
            });

            if (product) {
              const uniqueLots = [];
                let first_fifo;
                let is_merge= false;
                if (product.tracking == 'serial' || product.tracking == "lot") {

                    if(product.tracking == "lot"){

                         is_merge = true
                    }


                    const domain = [
                        ['ref', '=', barcode.barcode],
                        ['is_used', '=', false],
                        ['name', 'not in', lotNames],
//                        ['location_id', '=', 8]
                    ];
                    try {
                        const brander_serial_nos = await this.orm.call('stock.lot', 'search_read', [domain,['id', 'name', 'ref', 'rs_price',"mr_price","is_under_plan"]]);

                         const seenPrices = new Set();


                    for (const lot of brander_serial_nos) {
                        if (!seenPrices.has(lot.rs_price)) {
                            seenPrices.add(lot.rs_price);
                            uniqueLots.push(lot);
                        }
                    }

                     console.log("Serials with distinct prices:", uniqueLots);



                        first_fifo = brander_serial_nos[0];


                        first_fifo = brander_serial_nos[0];

                        if (first_fifo.is_under_plan == true){

                         return await this.popup.add(ErrorPopup, {
            title: _t("Under Audit Plan"),
            body: _t("Serial Number " + `${lotBarcode.code}` + " Under Audit Plan"),
        });
                        }
                    } catch (error) {
                        console.error("Error fetching stock lot:", error);
                    }

                    console.log(first_fifo);
                }

                if (first_fifo) {
                    const codeDetails = {
                        'base_code': first_fifo.name,
                        'code': first_fifo.name,
                        'type': "lot",
                        'value': first_fifo.name,
                    };

                    const options = await product.getAddProductOptions(codeDetails);
                    options.price = first_fifo.rs_price;
//                    options.merge = is_merge;
                    console.log("123",options);

                    if (code.type === "price") {
                        Object.assign(options, {
                            price: code.value,
                            extras: {
                                price_type: "manual",
                            },
                        });
                    } else if (code.type === "weight" || code.type === "quantity") {
                        Object.assign(options, {
                            quantity: code.value,
                            merge: false,
                        });
                    } else if (code.type === "discount") {
                        Object.assign(options, {
                            discount: code.value,
                            merge: false,
                        });
                    }
                    if (product.tracking === 'lot' && product.nhcl_product_type=='unbranded') {
        const lot_name = first_fifo.name;
        const existing_line = orderlines.find(orderline => {
            return orderline.product.id === product.id &&
                   orderline.pack_lot_lines.some(pack => pack.lot_name === lot_name);
        });

        if (existing_line) {
            // Increase the existing line’s quantity by 1 (or whatever increment you prefer)
            existing_line.set_quantity(existing_line.get_quantity() + 1);
            this.currentOrder._updateRewards();
            await this.customer();
            return; // ✅ stop here, don’t add a new line
        }
    }

                    selectedOrder.add_product(product, options);
                    this.currentOrder._updateRewards();
                    this.numberBuffer.reset();

                      if(uniqueLots.length>1){

                     const lotList = uniqueLots.map((lot) => {
                                        return {
                                            id: lot.id,
                                            item: lot,
                                            label: `MRP ₹${lot.mr_price} - Rsp Price ₹${lot.rs_price}`,
                                            isSelected: false,
                                        };
                                    });


                    const { confirmed, payload: selectedLot } = await this.popup.add(SelectionPopup, {
                        title: _t("Select Price"),
                        list: lotList,
                    });

                    if (!confirmed || !selectedLot) {
                        return;
                    }

                    // Do something with selectedLot
                    console.log('Selected unique lot:', selectedLot);

                    const selectedLine = this.currentOrder.get_selected_orderline();

                    const packLotLines = selectedLine.pack_lot_lines;

                      for (const lotLine of packLotLines) {
        selectedLine.pack_lot_lines.remove(lotLine);
    }

       let newPackLotLine;

        newPackLotLine = new Packlotline({ env: this.env }, { order_line: selectedLine });
        newPackLotLine.lot_name = selectedLot.name;
        selectedLine.pack_lot_lines.add(newPackLotLine);






                    }
                    await this.customer();
                }

                if (product.tracking != 'serial' && product.tracking!= 'lot') {
                    const options = await product.getAddProductOptions(barcode.barcode);

                    if (!options) {
                        return;
                    }

                    // Add the code for different `code.type` values here
                    if (code.type === "price") {
                        Object.assign(options, {
                            price: code.value,
                            extras: {
                                price_type: "manual",
                            },
                        });
                    } else if (code.type === "weight" || code.type === "quantity") {
                        Object.assign(options, {
                            quantity: code.value,
                            merge: false,
                        });
                    } else if (code.type === "discount") {
                        Object.assign(options, {
                            discount: code.value,
                            merge: false,
                        });
                    }

                    selectedOrder.add_product(product, options);
                    this.currentOrder._updateRewards();
                    this.numberBuffer.reset();
                    await this.customer();
                }
            } else {
                return true;
            }
        } else if (barcode.product_tmpl_id) {
            let list = self.env.services.pos.db.search_product_in_category(0, code.base_code);
            if (list.length == 1) {

                selectedOrder.add_product(list[0], { quantity: 1 });

                this.currentOrder._updateRewards();
                await this.customer();

                return true;
            } else {
                return false;
            }
        } else {
            return false;
        }
    } else {
        super._barcodeProductAction(code);
    }
},



    async _barcodeGS1Action(parsed_results) {
        const orderlines = await this.currentOrder.orderlines;
        const lotNames = [];

        orderlines.forEach(orderline => {
            if (orderline.product.tracking == 'serial' && orderline.pack_lot_lines.length > 0) {
                const packLotLines = orderline.pack_lot_lines;
                packLotLines.forEach(packLotLine => {
                    lotNames.push(packLotLine.lot_name);
                });
            }
        });

        const { product, lotBarcode, customProductOptions } = await this._parseElementsFromGS1(parsed_results);
        console.log('lotBarcode', lotBarcode);

        const domain = [['name', '=', lotBarcode.code]];
        let unbranded_serial_number = [];
        try {
            unbranded_serial_number = await this.orm.call('stock.lot', 'search_read', [domain]);
            if (unbranded_serial_number[0].is_under_plan){
                return await this.popup.add(ErrorPopup, {
                title: _t("Under Audit Plan"),
                body: _t("Serial Number " + `${lotBarcode.code}` + " Under Audit Plan"),
            });
            }

        } catch (error) {
            console.error("Error fetching unbranded serial number:", error);
        }

        console.log(unbranded_serial_number);

        if (lotNames.includes(lotBarcode.code)) {
            return await this.popup.add(ErrorPopup, {
                title: _t("Serial Number Duplication Not Allowed"),
                body: _t("Serial Number " + `${lotBarcode.code}` + " already exists in the Order"),
            });
        } else {
            if (!product) {
                const productBarcode = parsed_results.find((element) => element.type === "product");
                return this.popup.add(ErrorPopup, { code: productBarcode.base_code });
            }
            const options = await product.getAddProductOptions(lotBarcode);

            options.price = unbranded_serial_number.length > 0 ? unbranded_serial_number[0].rs_price : 0;
            if (product.tracking === 'lot' && product.nhcl_product_type=='unbranded') {
        const lot_name = unbranded_serial_number.length > 0 ? unbranded_serial_number[0].name : '';
        const existing_line = orderlines.find(orderline => {
            return orderline.product.id === product.id &&
                   orderline.pack_lot_lines.some(pack => pack.lot_name === lot_name);
        });

        if (existing_line) {
            // Increase the existing line’s quantity by 1 (or whatever increment you prefer)
            existing_line.set_quantity(existing_line.get_quantity() + 1);
            this.numberBuffer.reset();
            this.currentOrder._updateRewards();
            await this.customer();
            return; // ✅ stop here, don’t add a new line
        }
    }



            await this.currentOrder.add_product(product, { ...options, ...customProductOptions });
            this.numberBuffer.reset();

            this.currentOrder._updateRewards();
            await this.customer();
        }

        console.log(lotBarcode.code);
    },

    async updateSelectedOrderline({ buffer, key }) {
        const selectedLine = this.currentOrder.get_selected_orderline();
        if (key === "-") {
            if (selectedLine && selectedLine.eWalletGiftCardProgram) {
                // Do not allow negative quantity or price in a gift card or ewallet orderline.
                // Refunding gift card or ewallet is not supported.
                this.notification.add(
                    _t("You cannot set negative quantity or price to gift card or ewallet."),
                    4000
                );
                return;
            }
        }
        if (
            selectedLine &&
            selectedLine.is_reward_line &&
            !selectedLine.manual_reward &&
            (key === "Backspace" || key === "Delete")
        ) {
            const reward = this.pos.reward_by_id[selectedLine.reward_id];
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: _t("Deactivating reward"),
                body: _t(
                    "Are you sure you want to remove %s from this order?\n You will still be able to claim it through the reward button.",
                    reward.description
                ),
                cancelText: _t("No"),
                confirmText: _t("Yes"),
            });
            if (confirmed) {
                if (reward.discount_applicability != 'order') {
                    for (var promodiscline of selectedLine.promodisclines) {
                        if (promodiscline) {
                            var remove_line = this.currentOrder.get_orderlines().find(
                                (line) => line.cid === promodiscline);
                            remove_line.promo = 0;
                        } else {
                            continue;
                        }
                    }
                }
                buffer = null;
            } else {
                // Cancel backspace
                return;
            }
        }
        return super.updateSelectedOrderline({ buffer, key });
    },

    async customer() {
        const selectedOrderline = this.pos.get_order().get_selected_orderline();

        if (!selectedOrderline) {
            return;
        }

        const { confirmed, payload: inputValue } = await this.popup.add(CustomButtonPopup, {
            startingValue: "",
            title: _t("Add SALE PERSON"),
        });

        const emp_yes = await this.orm.call('hr.employee', 'search_read', [[]]);

        const value = inputValue || ""; // Ensure inputValue is a string
        const e = emp_yes.find((emp) => emp.barcode === value.trim());

        console.log("dsfsdfsdfd", value, e);

        if (value.trim() == "") {
            await this.popup.add(ErrorPopup, {
                title: _t("Sales employee mandatory"),
                body: _t("Please Enter Sales Person Id."),
            });
            return this.customer();
        }

        if (!e) {
            await this.popup.add(ErrorPopup, {
                title: _t("Please Enter Correct Id"),
                body: _t("Please Try Again"),
            });
            return this.customer();
        }

        selectedOrderline.set_emp_no(e.name);
        selectedOrderline.set_badge_id(e.barcode);
        selectedOrderline.set_employee_id(e.id);
        return true;
    },




async get_credit_details() {
    const partner = this.currentOrder.get_partner();

    if (!partner) {
        await this.popup.add(ErrorPopup, {
            title: _t("Customer Mandatory"),
            body: _t("Please add a customer and try again"),
        });
        return;
    }

    const credit_details = await this.pos.get_redeem_amount(partner.id);
    if (credit_details && credit_details.length >= 1) {
        const creditDetailsList = credit_details.map((credit) => ({
            id: credit.id,
            item: credit,
            label: `VC NO ${credit.voucher_number} - Amount ₹${credit.remaining_amount}`,
            isSelected: false,
        }));

        const { confirmed, payload: selectedCredits } = await this.popup.add(SelectionPopup, {
            title: _t("Select Credit"),
            list: creditDetailsList,
            multi: true,
        });

        const normalizedCredits = Array.isArray(selectedCredits)
    ? selectedCredits
    : [selectedCredits];

    if (!confirmed || normalizedCredits.length === 0) {
    return;
    }

        // Assign selected credit data to current order
        for (const normalizedCredit of normalizedCredits) {
          if (this.currentOrder.credit_ids && this.currentOrder.credit_ids.includes(normalizedCredit.id)){
         await this.popup.add(ErrorPopup, {
            title: _t("Credit Note Already added"),
            body: _t("The customer Credit Note Already added in this order."),
        });
        return
         }
        }


        this.currentOrder.credit_note_amount = normalizedCredits.reduce(
    (sum, credit) => sum + credit.remaining_amount, 0
);
this.currentOrder.credit_id = normalizedCredits[0]['id']

        this.currentOrder.credit_ids = [
...this.currentOrder.credit_ids,
    ...normalizedCredits.map(credit => credit.id)
];


        this.currentOrder.credit_partner = partner.id;
    } else {
        await this.popup.add(ErrorPopup, {
            title: _t("No Credit Available"),
            body: _t("This customer has no redeemable credit notes."),
        });
    }
},


});
