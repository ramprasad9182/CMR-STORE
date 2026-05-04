/** @odoo-module **/
import { Component, useState, useEffect, useRef, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { _t } from "@web/core/l10n/translation";


export class CustomSearch extends Component {
   static components = { Input };
    static template = "nhcl_pos_sale.CustomSearch";
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.barcodeReader = useService("barcode_reader");
        this.orm = useService("orm");


        this._autoFocusEnabled = true;

        document.addEventListener("click", (ev) => {
            const input = document.querySelector(".custom-search input[type='text']");
            // const input = document.querySelector(".custom-search input");

            if (input && !input.contains(ev.target)) {
                this._autoFocusEnabled = false;
            }
        });

        setTimeout(() => {
            this._focusInput();
        }, 300);

        onMounted(() => {
            this._focusInput();
            this._focusInterval = setInterval(() => {
                this._focusInput();
            }, 800);
        });
    }

    _focusInput() {
        if (!this._autoFocusEnabled) {
            return;
        }
        const popup = document.querySelector(
            ".modal-dialog, .popup, .o-dialog-container"
        );
        if (popup) {
            return;
        }
        const input = document.querySelector(".custom-search input");
        if (input && document.activeElement !== input) {
            input.focus();
        }
    }

    async handleKeyDown(event) {
        if (event.key !== 'Enter') {
            return;
        }
        event.preventDefault();
        this.showLoadingIndicator = true;
        try {
            const inputValue = event.target.value.trim();
            if (!inputValue) {
                return;
            }
            if (inputValue.toLowerCase().startsWith('r')) {
                const formattedValue = 'R' + inputValue.slice(1);
                const lots = await this.orm.call(
                    'stock.lot',
                    'search_read',
                    [[['name', '=', formattedValue]]],
                    { limit: 1 }
                );
                const lot = lots && lots[0];
                if (lot) {
                    const products = await this.orm.call(
                        'product.product',
                        'search_read',
                        [[['id', '=', lot.product_id[0]]]],
                        {
                            fields: ['id', 'barcode', 'qty_available', 'nhcl_product_type'],
                            limit: 1
                        }
                    );
                    const product = products && products[0];
                    if (!lot.product_qty_pos || lot.product_qty_pos <= 0) {
                        this.pos.env.services.popup.add(ErrorPopup, {
                            title: "No Stock Available",
                            body: "This item has no on-hand quantity.",
                        });
                        return;
                    }
                    const lot_damage_return_location = this.pos.stock_location.filter(
                        (l) =>
                            l.id === lot.location_id[0] &&
                            l.cmr_location_type &&
                            ["damage_location", "return_location"].includes(l.cmr_location_type)
                    );
                    if (lot_damage_return_location.length > 0) {
                        this.pos.env.services.popup.add(ErrorPopup, {
                            title: _t("Wrong Location Error"),
                            body: _t(
                                'This item has on %s location. please move to Main location.\n For that please click on Damage-Main/Return-Main button',
                                lot_damage_return_location[0].name
                            ),
                        });
                        return;
                    }
                    if (product && product.nhcl_product_type === 'branded') {
                        this.pos.env.services.popup.add(ErrorPopup, {
                            title: 'Entry Not Allowed',
                            body: 'All Branded products must be scanned using the barcode only.',
                        });
                        return;
                    }
                    if (product && product.barcode) {
                        this.barcodeReader.scan(`01${product.barcode}21${formattedValue}`);
                    } else {
                        this.barcodeReader.scan(formattedValue);
                    }
                } else {
                    this.barcodeReader.scan(formattedValue);
                }
            } else {
                this.barcodeReader.scan(inputValue);
            }
        } catch (error) {
            console.error('Error processing input:', error);
        } finally {
            this.showLoadingIndicator = false;
            this.pos.searchProductByCode = "";
            event.target.value = "";
            event.target.dispatchEvent(new Event('input'));
            this._autoFocusEnabled = true;
            this._focusInput();

        }
    }
}