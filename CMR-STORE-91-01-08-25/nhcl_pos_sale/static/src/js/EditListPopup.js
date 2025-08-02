/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { jsonrpc } from "@web/core/network/rpc_service";
import { EditListPopup } from "@point_of_sale/app/store/select_lot_popup/select_lot_popup";
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";
    /**
     * EditListPopup Override
     *
     * This module overrides the EditListPopup component in the Point of Sale (POS) module
     * to add custom behavior for serial number validation.
     */
patch (EditListPopup.prototype, {
    setup() {
        super.setup();
        this.pos=usePos();
        this.popup = useService("popup");
        this.notification = useService("notification");

    },
            /**
             * On confirming from the popup after adding lots/ serial numbers,
             * the values are passed to the function validate_lots() for the
             * validation. The corresponding error messages will be displayed
             * on the popup if the lot is invalid or duplicated, or there is
             * no insufficient stock.
             */
           async confirm() {
                if (this.props.title == 'Lot/Serial Number(s) Required'){
                    var lot_string = this.state.array
//                    console.log(lot_string)
                    var lot_names = [];
                    for (var i = 0; i < lot_string.length; i++) {
                        if (lot_string[i].text != ""){
                            lot_names.push(lot_string[i].text);
                        }
                    }
                    var self = this;
                    if(lot_names.length ==0 ){
                    self.notification.add(_t("Please Enter a Serial Number."), { type: 'danger' });
                            return false;
                        }
                    let cnt = 0;
                    let undef_serial_ids = [];
                    for (let eachItem of lot_names){
                              if (this.pos.stock_lots_by_name[eachItem]){
                              cnt++;
                              }
                              else{
                              undef_serial_ids.push(eachItem)
                              }

                        }
                    console.log("undef_serials",undef_serial_ids)
                    console.log("cnt",cnt)
                    if (cnt == lot_names.length){
                    self.props.close({ confirmed: true, payload: self.getPayload() });
                    }
                    else {
                    self.env.services.popup.add(ErrorPopup, {
                            title: _t("Invalid Lot/ Serial Number"),
                            body: _t(
                                "The Lot/ Serial Number [ " + undef_serial_ids + ' ] is not available for this product.'
                            ),
                        });
                         return false;
                    }
        }

                else{
//                this.props.close({ confirmed: true, payload: this.getPayload() });
                return true;
                }
            },
});
