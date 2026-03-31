/** @odoo-module **/
import { Component, useState, useEffect, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";


export class CustomSearch extends Component {
   static components = { Input };
    static template = "nhcl_pos_sale.CustomSearch";
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.barcodeReader = useService("barcode_reader");
        this.orm = useService("orm");
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

            // ---------- MANUAL ENTRY FLOW ----------
            if (inputValue.toLowerCase().startsWith('r')) {
                const formattedValue = 'R' + inputValue.slice(1);

                // Find the lot / serial
                const lots = await this.orm.call(
                    'stock.lot',
                    'search_read',
                    [[['name', '=', formattedValue]]],
                    { limit: 1 }
                );

                const lot = lots && lots[0];

                if (lot) {
                    // Fetch related product
                    const products = await this.orm.call(
                        'product.product',
                        'search_read',
                        [[['id', '=', lot.product_id[0]]]],
                        { limit: 1 }
                    );

                    const product = products && products[0];


                    // BLOCK ONLY: branded + serial MANUAL ENTRY
                    if (
                        product &&
                        product.nhcl_product_type === 'branded'
                    ) {
                        //  DO NOT scan
                        setTimeout(() => {
                            this.pos.env.services.popup.add(ErrorPopup, {
                                title: 'Entry Not Allowed',
                                body: 'All Branded products must be scanned using the barcode only.',
                            });
                        }, 0);

                        // Cleanup
                        event.target.value = '';
                        this.pos.searchProductByCode = '';
                        event.target.blur();

                        return; // STOP here (manual flow only)
                    }

                    // Allowed → build GS1 and scan
                    if (product && product.barcode) {
                        this.barcodeReader.scan(
                            `01${product.barcode}21${formattedValue}`
                        );
                    } else {
                        this.barcodeReader.scan(formattedValue);
                    }
                } else {
                    // Serial not found → fallback to barcode flow
                    this.barcodeReader.scan(formattedValue);
                }
            }
            // ---------- NORMAL SCAN FLOW ----------
            else {
                this.barcodeReader.scan(inputValue);
            }

            // ---------- CLEANUP ----------
            event.target.value = '';
            this.pos.searchProductByCode = '';
            event.target.blur();

        } catch (error) {
            console.error('Error processing input:', error);
        } finally {
            this.showLoadingIndicator = false;
        }
    }

}