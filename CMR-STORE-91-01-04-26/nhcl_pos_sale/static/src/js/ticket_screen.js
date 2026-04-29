/** @odoo-module */

import {Component, onWillStart} from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    setup() {
        super.setup();
        this.show_delete_button = false;
        this.select_all_ongoing_order_in_ticket_screen = false;
//        this.pos = usePos();
//        this.delete_order_access = this.pos.user.allow_delete_order_button;

        for (const order of this.getFilteredOrderList()) {
            order.select_order_in_ticket_screen = false;
        }

        onWillStart(async () => {
            this._keyHandler = async (ev) => {
                if (ev.shiftKey && ev.key.toLowerCase() === "a") {
                    ev.preventDefault();
                    ev.stopPropagation();
                    this.onClickAllSelectOrders();
                } else if (ev.ctrlKey && ev.key.toLowerCase() === "r") {
                    ev.preventDefault();
                    ev.stopPropagation();
                    await this.onClickDeleteSelectedOrders();
                }
            };

            window.addEventListener("keydown", this._keyHandler);
        });
    },

    willUnmount() {
        super.willUnmount();
        window.removeEventListener("keydown", this._keyHandler);
    },

    onClickAllSelectOrders() {
        let select_order_in_ticket_screen = false
        if (this.select_all_ongoing_order_in_ticket_screen) {
            this.select_all_ongoing_order_in_ticket_screen = false;
            select_order_in_ticket_screen = false;
        } else {
            this.select_all_ongoing_order_in_ticket_screen = true;
            select_order_in_ticket_screen = true;
        }
        for (const order of this.getFilteredOrderList()) {
            if (order.select_order_in_ticket_screen) {
                order.select_order_in_ticket_screen = select_order_in_ticket_screen;
                this.show_delete_button = select_order_in_ticket_screen;
            } else {
                order.select_order_in_ticket_screen = select_order_in_ticket_screen;
                this.show_delete_button = select_order_in_ticket_screen;
            }
        }
    },

    onClickSelectOrder(order) {
        if (order.select_order_in_ticket_screen) {
            order.select_order_in_ticket_screen = false;
        } else {
            order.select_order_in_ticket_screen = true;
        }
        const filteredOrders = this.getFilteredOrderList().filter(order => order.select_order_in_ticket_screen === true);
        if (filteredOrders.length > 0) {
            this.show_delete_button = true;
        } else {
            this.show_delete_button = false;
        }
    },

    async onClickDeleteSelectedOrders() {
        for (const order of this.getFilteredOrderList()) {
            if (order.select_order_in_ticket_screen) {
//                await this.onDeleteOrder(order);
                if (order && (await this._onBeforeDeleteOrder(order))) {
                    if (Object.keys(order.lastOrderPrepaChange).length > 0) {
                        await this.pos.sendOrderInPreparationUpdateLastChange(order, true);
                    }
                    if (order === this.pos.get_order()) {
                        this._selectNextOrder(order);
                    }
                    this.pos.removeOrder(order);
                    if (this._state.ui.selectedOrder === order) {
                        if (this.pos.get_order_list().length > 0) {
                            this._state.ui.selectedOrder = this.pos.get_order_list()[0];
                        } else {
                            this._state.ui.selectedOrder = null;
                        }
                    }
                }
                if (this.pos.isOpenOrderShareable()) {
                    await this.pos._removeOrdersFromServer();
                }
                // this.db.remove_order(reactiveOrder.uid);
            }
        }
        this.show_delete_button = false;
    },

    async onFilterSelected(selectedFilter) {
        this._state.ui.filter = selectedFilter;
        if (!selectedFilter) {
            this._state.ui.filter = "ONGOING";
        }

        if (this._state.ui.filter == "ACTIVE_ORDERS" || this._state.ui.filter === null) {
            this._state.ui.selectedOrder = this.pos.get_order();
        }
        if (this._state.ui.filter == "SYNCED") {
            await this._fetchSyncedOrders();
        }
    },

    _getOrderStates() {
        // We need the items to be ordered, therefore, Map is used instead of normal object.
        const states = new Map();
        // states.set("ACTIVE_ORDERS", {
        //     text: _t("All active orders"),
        // });
        // The spaces are important to make sure the following states
        // are under the category of `All active orders`.
        states.set("ONGOING", {
            text: _t("Ongoing"),
            indented: true,
        });
        states.set("ACTIVE_ORDERS", {
            text: _t("All active orders"),
            indented: true,
        });
        states.set("PAYMENT", {
            text: _t("Payment"),
            indented: true,
        });
        states.set("RECEIPT", {
            text: _t("Receipt"),
            indented: true,
        });
        return states;
    },
});
