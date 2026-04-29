/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { useState } from "@odoo/owl";

patch(SelectionPopup.prototype, {
    setup() {
        super.setup();
        this.state = useState({
            search: "",
        });
    },

    get filteredList() {
        const search = this.state.search.trim().toLowerCase();

        if (!search) {
            return this.props.list;
        }

        const startsWith = [];
        const includes = [];

        for (const item of this.props.list) {
            const name = (item.label || "").toLowerCase();

            if (name.startsWith(search)) {
                startsWith.push(item);
            } else if (name.includes(search)) {
                includes.push(item);
            }
        }

        // Priority: startsWith first
        return [...startsWith, ...includes];
    }
});