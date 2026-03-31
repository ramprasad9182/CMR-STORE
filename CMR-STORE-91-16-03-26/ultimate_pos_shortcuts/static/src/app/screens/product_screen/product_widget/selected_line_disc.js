/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();

        const handleKeyPress = (e) => {
            if (!(e instanceof KeyboardEvent)) return;

            // Check for Ctrl+5
            if (e.shiftKey && (e.key === 'd' || e.key === 'D')) {
                e.preventDefault();
                e.stopImmediatePropagation();
                e.stopPropagation();
                e.stopImmediatePropagation();

                // Look for button that contains discount text
                const buttons = document.querySelectorAll('.control-button');
                for (let button of buttons) {
                    if (Object.keys(this.popup.popups).length === 0) {
                        if (button.textContent.includes('Selected Lines Discount') ||
                            button.querySelector('.fa-scissors')) {
                            button.click();
                            continue;
                        }
                    }
                }
            }
        };

        window.addEventListener('keydown', handleKeyPress);

        // Clean up
        this.__discountShortcutCleanup = () => {
            window.removeEventListener('keydown', handleKeyPress);
        };
    },

    destroy() {
        if (this.__discountShortcutCleanup) {
            this.__discountShortcutCleanup();
        }
        super.destroy();
    }
});