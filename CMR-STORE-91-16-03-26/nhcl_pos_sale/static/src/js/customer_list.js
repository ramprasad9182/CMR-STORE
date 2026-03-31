/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerListScreen } from "@point_of_sale/app/screens/partner_list/partner_list";
import { session } from "@web/session";

patch(PartnerListScreen.prototype, {
    setup() {
        super.setup();

        this._keyHandler = (ev) => {
            if (ev.ctrlKey && ev.key.toLowerCase() === "s") {
                ev.preventDefault();
                ev.stopPropagation();
                this.createPartner();
            }
        };

        window.addEventListener("keydown", this._keyHandler);
    },

    willUnmount() {
        super.willUnmount();
        window.removeEventListener("keydown", this._keyHandler);
    },

    createPartner() {
        const { country_id, state_id } = this.pos.company;

        let defaultValue = "";

        if (this.state.query && this.state.query.trim() !== "") {
            const searchValue = this.state.query.trim();

            // check if no partner found
            const partners = this.pos.db.search_partner(searchValue);
            if (partners.length === 0) {
                defaultValue = searchValue;
            }
        }

        this.state.editModeProps.partner = {
            country_id,
            state_id,
            lang: session.user_context.lang,
//            phone: defaultValue,
//            name: defaultValue,
        };

        if (/^[0-9]+$/.test(defaultValue)) {
            this.state.editModeProps.partner.phone = defaultValue;
        } else {
            this.state.editModeProps.partner.name = defaultValue;
        }

        this.activateEditMode();
    },

});