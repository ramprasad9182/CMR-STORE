/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

export class MultiSelectionPopup extends AbstractAwaitablePopup {
    static template = "nhcl_pos_sale.MultiSelectionPopup";
    static defaultProps = {
        confirmText: _t("ADD"),
        cancelText: _t("Cancel"),
        title: _t("Select"),
        body: "",
        list: [],
        confirmKey: false,
    };

    setup() {
        super.setup();
        this.state = useState({
            selectedIds: this.props.list
                .filter((item) => item.isSelected)
                .map((item) => item.id),
        });
//        this.props.total_credit_amount
    }

    selectItem(item) {
        const index = this.state.selectedIds.indexOf(item.id);

        if (index > -1) {
            this.state.selectedIds.splice(index, 1); // remove if exists
            this.props.list.filter((i) => i.id === item.id)[0].isSelected = false;
            this.props.total_credit_amount -= item.amount;
        } else {
            this.state.selectedIds.push(item.id); // add if not exists
            this.props.list.filter((i) => i.id === item.id)[0].isSelected = true;
            this.props.total_credit_amount += item.amount;
        }
    }

    /**
     * We send as payload of the response the selected item.
     *
     * @override
     */
    getPayload() {
        const selectedItems = this.props.list
            .filter((item) => this.state.selectedIds.includes(item.id))
            .map((item) => item.item);
        return selectedItems;
    }
}
