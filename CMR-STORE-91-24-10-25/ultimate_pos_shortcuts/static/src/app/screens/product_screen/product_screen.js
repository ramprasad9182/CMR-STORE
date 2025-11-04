/** @odoo-module */

import { registry } from "@web/core/registry";
import { ProductScreen as BaseProductScreen} from "@point_of_sale/app/screens/product_screen/product_screen";
import { Numpad } from "@point_of_sale/app/generic_components/numpad/numpad";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { useEffect, useState  } from "@odoo/owl";
import { CustomSearch } from "@nhcl_pos_sale/app/screens/product_screen/custom_search/custom_search";
import { OrderSummaryPopup } from "@nhcl_pos_sale/app/screens/product_screen/custom_search/order_summary";


import { ActionpadWidget } from "@ultimate_pos_shortcuts/app/screens/product_screen/actionpad_widget/actionpad_widget";
import { ProductsWidget } from "@ultimate_pos_shortcuts/app/screens/product_screen/product_widget/product_widget";

export class ProductScreen extends BaseProductScreen {
    static components = {
        ActionpadWidget,
        Numpad,
        ProductsWidget,
        Orderline,
        OrderWidget,
        CustomSearch,
        OrderSummaryPopup,

    };
    setup() {
        super.setup();
        this.state = useState({ orderIndex : -1});
        const handleKeyPress = (e) => {
            if(e instanceof KeyboardEvent){
                if(e.key === 'ArrowUp'){
                    this.syncOrderIndex();
                    if (this.state.orderIndex > 0) {
                        this.decreaseOrderIndex();
                        this.selectLine(this.orderline[this.state.orderIndex])
                    }
                }
                else if(e.key === 'ArrowDown'){
                    this.syncOrderIndex();
                    if (this.state.orderIndex < this.orderline.length - 1) {
                        this.increaseOrderIndex();
                        this.selectLine(this.orderline[this.state.orderIndex])
                    }
                }
                else if(e.shiftKey && (e.key === 'E' || e.key === 'E')){
                    const refund = this.controlButtonsRef[0];
                    refund.click();
                }
                else if(e.shiftKey && (e.key === 'n' || e.key === 'N')){
                    const customerNote = this.controlButtonsRef[2];
                    customerNote.click();
                }
                else if(e.shiftKey && (e.key === 'q' || e.key === 'Q')){
                    this.pos.numpadMode = 'quantity';

                }
                else if(e.shiftKey && (e.key === 'D' || e.key === 'd')){
                    this.pos.numpadMode = 'discount';
                }
                else if(e.shiftKey && (e.key === 'P' || e.key === 'p')){
                    this.pos.numpadMode = 'price';
                }
                else if(e.shiftKey && (e.key == 'C' || e.key == 'c')){
                    this.pos.selectPartner();
                }
            }

        };

        useEffect(() => {
            document.body.addEventListener('keyup', handleKeyPress);

            return () => {
                document.body.removeEventListener('keyup', handleKeyPress);
            };
        });

    }

    increaseOrderIndex() {
        this.state.orderIndex++;
    }
    decreaseOrderIndex() {
        this.state.orderIndex--;
    }
    syncOrderIndex() {
        this.state.orderIndex = this.selectedOrderlineIndex;
    }

    get controlButtonsRef(){
        return document.body ? document.body.getElementsByClassName('control-button') : [];
    }

    get orderline(){
        const order = this.pos.get_order();
        const orderlines = order.orderlines;
        return orderlines;
    }
    get selectedOrderline(){
        const order = this.pos.get_order();
        return  order.get_selected_orderline();
    }
    get selectedOrderlineIndex() {
        let index = -1;
        for(let i=0;i < this.orderline.length;i++){
            if(this.selectedOrderline.id === this.orderline[i].id){
                index = i;
            }
        }
        return index;
    }

}

registry.category("pos_screens").remove("ProductScreen");
registry.category("pos_screens").add("ProductScreen", ProductScreen);
